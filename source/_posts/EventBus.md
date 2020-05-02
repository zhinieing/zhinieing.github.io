---
title: EventBus
date: 2017-12-27 13:52:33
categories:
- 开源库
tags:
- Android
- library
---
> EventBus 基于观察者模式的 Android 事件分发总线。它使得 事件发送 和 事件接收 很好地解耦。另外使得 Android 组件之间的通信变得简单，代码变得整洁。

<!--more-->

**EventBus 的三个步骤**

1. 注册订阅者
2. 事件发布
3. 反注册订阅者


## 注册订阅者

```Java
EventBus.getDefault().register(this);
```

`getDefault()`是一个`DoubleCheckLock`的单例模式获取到实例。再看一下 EventBus 的构造方法

```Java
public EventBus() {
    this(DEFAULT_BUILDER);
}

EventBus(EventBusBuilder builder) {
    subscriptionsByEventType = new HashMap<>();
    typesBySubscriber = new HashMap<>();
    stickyEvents = new ConcurrentHashMap<>();
    mainThreadPoster = new HandlerPoster(this, Looper.getMainLooper(), 10);
    backgroundPoster = new BackgroundPoster(this);
    asyncPoster = new AsyncPoster(this);
    indexCount = builder.subscriberInfoIndexes != null ? builder.subscriberInfoIndexes.size() : 0;
    subscriberMethodFinder = new SubscriberMethodFinder(builder.subscriberInfoIndexes,
            builder.strictMethodVerification, builder.ignoreGeneratedIndex);
    logSubscriberExceptions = builder.logSubscriberExceptions;
    logNoSubscriberMessages = builder.logNoSubscriberMessages;
    sendSubscriberExceptionEvent = builder.sendSubscriberExceptionEvent;
    sendNoSubscriberEvent = builder.sendNoSubscriberEvent;
    throwSubscriberException = builder.throwSubscriberException;
    eventInheritance = builder.eventInheritance;
    executorService = builder.executorService;
}

public EventBus build() {
    return new EventBus(this);
}
```

默认的构造方法又调用参数为`EventBusBuilder`的构造方法，构造出 EventBus 的实例。

接下来看`register()`

```Java
public void register(Object subscriber) {
    Class<?> subscriberClass = subscriber.getClass();
    // 获取订阅者的订阅方法并用List封装
    List<SubscriberMethod> subscriberMethods = subscriberMethodFinder.findSubscriberMethods(subscriberClass);
    synchronized (this) {
        // 逐个订阅
        for (SubscriberMethod subscriberMethod : subscriberMethods) {
            subscribe(subscriber, subscriberMethod);
        }
```

`register()`接收参数为 Object 类型的订阅者，通常也就是代码中 Activity 和 Fragment 的实例 this。`subscriberMethodFinder`是 EventBus 的一个成员，可以看作是一个订阅方法查找器。调用`findSubscriberMethods`方法，传入订阅者的 Class 对象，字面意思是找出订阅者中所有的订阅方法，用一个 List 集合来接收。

```Java
List<SubscriberMethod> findSubscriberMethods(Class<?> subscriberClass) {
    List<SubscriberMethod> subscriberMethods = METHOD_CACHE.get(subscriberClass);
    if (subscriberMethods != null) {
        return subscriberMethods;
    }
    if (ignoreGeneratedIndex) {
        // 使用反射方式获取
        subscriberMethods = findUsingReflection(subscriberClass);
    } else {
        // 使用SubscriberIndex方式获取
        subscriberMethods = findUsingInfo(subscriberClass);
    }
    // 若订阅者中没有订阅方法，则抛异常
    if (subscriberMethods.isEmpty()) {
        throw new EventBusException("Subscriber " + subscriberClass
                + " and its super classes have no public methods with the @Subscribe annotation");
    } else {
        // 缓存订阅者的订阅方法List
        METHOD_CACHE.put(subscriberClass, subscriberMethods);
        return subscriberMethods;
    }
}
```

`METHOD_CACHE`是一个 Map，以订阅者的 Class 对象为 key，订阅者中的订阅方法 List 为 value，缓存了注册过的订阅方法。`ignoreGeneratedIndex`这个属性默认为 false，当为 tru 时，表示以反射的方式获取订阅者中的订阅方法，当为 false 时，则以`Subscriber Index`的方式获取。

```java
// 使用反射方式获取
private List<SubscriberMethod> findUsingReflection(Class<?> subscriberClass) {
    // 创建并初始化FindState对象
    FindState findState = prepareFindState();
    // findState与subscriberClass关联
    findState.initForSubscriber(subscriberClass);
    while (findState.clazz != null) {
        // 使用反射的方式获取单个类的订阅方法
        findUsingReflectionInSingleClass(findState);
        // 使findState.clazz指向父类的Class，继续获取
        findState.moveToSuperclass();
    }
    // 返回订阅者极其父类的订阅方法List，并释放资源
    return getMethodsAndRelease(findState);
}

private void findUsingReflectionInSingleClass(FindState findState) {
    Method[] methods;
    try {
        // This is faster than getMethods, especially when subscribers are fat classes like Activities
        methods = findState.clazz.getDeclaredMethods();
    } catch (Throwable th) {
        // Workaround for java.lang.NoClassDefFoundError, see https://github.com/greenrobot/EventBus/issues/149
        methods = findState.clazz.getMethods();
        findState.skipSuperClasses = true;
    }
    for (Method method : methods) {
        int modifiers = method.getModifiers();
        // 忽略非public的方法和static等修饰的方法
        if ((modifiers & Modifier.PUBLIC) != 0 && (modifiers & MODIFIERS_IGNORE) == 0) {
            // 获取订阅方法的所有参数
            Class<?>[] parameterTypes = method.getParameterTypes();
            // 订阅方法只能有一个参数，否则忽略
            if (parameterTypes.length == 1) {
                // 获取注解
                Subscribe subscribeAnnotation = method.getAnnotation(Subscribe.class);
                if (subscribeAnnotation != null) {
                    // 获取第一个参数
                    Class<?> eventType = parameterTypes[0];
                    // 检查eventType决定是否订阅，通常订阅者不能有多个eventType相同的订阅方法
                    if (findState.checkAdd(method, eventType)) {
                        // 获取线程模式
                        ThreadMode threadMode = subscribeAnnotation.threadMode();
                        // 添加订阅方法进List
                        findState.subscriberMethods.add(new SubscriberMethod(method, eventType, threadMode,
                                subscribeAnnotation.priority(), subscribeAnnotation.sticky()));
                    }
                }
            } else if (strictMethodVerification && method.isAnnotationPresent(Subscribe.class)) {
                String methodName = method.getDeclaringClass().getName() + "." + method.getName();
                throw new EventBusException("@Subscribe method " + methodName +
                        "must have exactly 1 parameter but has " + parameterTypes.length);
            }
        } else if (strictMethodVerification && method.isAnnotationPresent(Subscribe.class)) {
            String methodName = method.getDeclaringClass().getName() + "." + method.getName();
            throw new EventBusException(methodName +
                    " is a illegal @Subscribe method: must be public, non-static, and non-abstract");
        }
    }
}
```

经过修饰符、参数个数、是否有注解、和订阅者是否有`eventType`相同的方法几层条件的筛选，最终将订阅方法添加进`findState`的`subscriberMethods`这个 List 中。



```java
// 使用SubscriberIndex方式获取
private List<SubscriberMethod> findUsingInfo(Class<?> subscriberClass) {
    FindState findState = prepareFindState();
    findState.initForSubscriber(subscriberClass);
    while (findState.clazz != null) {
        // 获取当前clazz对应的SubscriberInfo
        findState.subscriberInfo = getSubscriberInfo(findState);
        if (findState.subscriberInfo != null) {
            // 通过SubscriberInfo获取阅方法数组
            SubscriberMethod[] array = findState.subscriberInfo.getSubscriberMethods();
            // 逐个添加进findState.subscriberMethods
            for (SubscriberMethod subscriberMethod : array) {
                if (findState.checkAdd(subscriberMethod.method, subscriberMethod.eventType)) {
                    findState.subscriberMethods.add(subscriberMethod);
                }
            }
        } else {
            // 若SubscriberInfo为空，则采用反射方式获取
            findUsingReflectionInSingleClass(findState);
        }
        findState.moveToSuperclass();
    }
}

private SubscriberInfo getSubscriberInfo(FindState findState) {
    if (findState.subscriberInfo != null && findState.subscriberInfo.getSuperSubscriberInfo() != null) {
        SubscriberInfo superclassInfo = findState.subscriberInfo.getSuperSubscriberInfo();
        if (findState.clazz == superclassInfo.getSubscriberClass()) {
            return superclassInfo;
        }
    }
    if (subscriberInfoIndexes != null) {
        for (SubscriberInfoIndex index : subscriberInfoIndexes) {
            // 通过SubscriberIndex获取findState.clazz对应的SubscriberInfo
            SubscriberInfo info = index.getSubscriberInfo(findState.clazz);
            if (info != null) {
                return info;
            }
        }
    }
    return null;
}
```

这时候主角出现了，我们看`subscriberInfoIndexes`，它是一个 List，类型为`Subscriber Index`，订阅者索引，是由 EventBus 注解处理器生成的。



无论通过哪种方式获取，获取到订阅方法 List 之后，接下来是真正订阅的过程。

```Java
synchronized (this) {
    for (SubscriberMethod subscriberMethod : subscriberMethods) {
        subscribe(subscriber, subscriberMethod);
    }
}
```

```Java
// Must be called in synchronized block
private void subscribe(Object subscriber, SubscriberMethod subscriberMethod) {
    Class<?> eventType = subscriberMethod.eventType;
    // 创建Subscription封装订阅者和订阅方法信息
    Subscription newSubscription = new Subscription(subscriber, subscriberMethod);
    // 根据事件类型从subscriptionsByEventType这个Map中获取Subscription集合
    CopyOnWriteArrayList<Subscription> subscriptions = subscriptionsByEventType.get(eventType);
    // 若Subscription集合为空，创建并put进Map中
    if (subscriptions == null) {
        subscriptions = new CopyOnWriteArrayList<>();
        subscriptionsByEventType.put(eventType, subscriptions);
    } else {
        // 若集合中已包含该Subscription则抛异常
        if (subscriptions.contains(newSubscription)) {
            throw new EventBusException("Subscriber " + subscriber.getClass() + " already registered to event "
                    + eventType);
        }
    }
    int size = subscriptions.size();
    for (int i = 0; i <= size; i++) {
        // 按照优先级插入Subscription
        if (i == size || subscriberMethod.priority > subscriptions.get(i).subscriberMethod.priority) {
            subscriptions.add(i, newSubscription);
            break;
        }
    }
    // typesBySubscriber与subscriptionsByEventType类似
    // 用来存放订阅者中的事件类型
    List<Class<?>> subscribedEvents = typesBySubscriber.get(subscriber);
    if (subscribedEvents == null) {
        subscribedEvents = new ArrayList<>();
        typesBySubscriber.put(subscriber, subscribedEvents);
    }
    subscribedEvents.add(eventType);
    // 订阅方法是否设置黏性模式
    if (subscriberMethod.sticky) {
        // 是否设置了事件继承
        if (eventInheritance) {
            // Existing sticky events of all subclasses of eventType have to be considered.
            // Note: Iterating over all events may be inefficient with lots of sticky events,
            // thus data structure should be changed to allow a more efficient lookup
            // (e.g. an additional map storing sub classes of super classes: Class -> List<Class>).
            Set<Map.Entry<Class<?>, Object>> entries = stickyEvents.entrySet();
            for (Map.Entry<Class<?>, Object> entry : entries) {
                Class<?> candidateEventType = entry.getKey();
                // 判断当前事件类型是否为黏性事件或者其子类
                if (eventType.isAssignableFrom(candidateEventType)) {
                    Object stickyEvent = entry.getValue();
                    // 执行设置了sticky模式的订阅方法
                    checkPostStickyEventToSubscription(newSubscription, stickyEvent);
                }
            }
        } else {
            Object stickyEvent = stickyEvents.get(eventType);
            checkPostStickyEventToSubscription(newSubscription, stickyEvent);
        }
    }
}
```

* `subscriptionsByEventType`：以事件类型为 key，拥有相同事件类型的订阅方法 List 为 value，存放所有的订阅方法。
* `typesBySubscriber`：以订阅者为 key，订阅者订阅的所有事件类型 List 为 value，存放所有的事件类型。



## 事件发布

```Java
EventBus.getDefault().post(new UpdateUIEvent());
```

```Java
/** Posts the given event to the event bus. */
public void post(Object event) {
    // 获取当前线程的posting状态
    PostingThreadState postingState = currentPostingThreadState.get();
    List<Object> eventQueue = postingState.eventQueue;
    // 将事件添加进当前线程的事件队列
    eventQueue.add(event);
    // 判断当前线程是否正在发布事件
    if (!postingState.isPosting) {
        postingState.isMainThread = Looper.getMainLooper() == Looper.myLooper();
        postingState.isPosting = true;
        // 取消发布状态没有重置，抛异常
        if (postingState.canceled) {
            throw new EventBusException("Internal error. Abort state was not reset");
        }
        try {
            while (!eventQueue.isEmpty()) {
                PostingThreadState(eventQueue.remove(0), postingState);
            }
        } finally {
            postingState.isPosting = false;
            postingState.isMainThread = false;
        }
    }
}
```

EventBus 用`ThreadLocal`存储每个线程的`PostingThreadState`，一个存储了事件发布状态的类，当 post 一个事件时，添加到事件队列末尾，等待前面的事件发布完毕后再拿出来发布，这里看事件发布的关键代码`PostingThreadState()`。

```Java
private void postSingleEvent(Object event, PostingThreadState postingState) throws Error {
    Class<?> eventClass = event.getClass();
    boolean subscriptionFound = false;
    if (eventInheritance) {
        List<Class<?>> eventTypes = lookupAllEventTypes(eventClass);
        int countTypes = eventTypes.size();
        for (int h = 0; h < countTypes; h++) {
            Class<?> clazz = eventTypes.get(h);
            // 发布事件
            subscriptionFound |= postSingleEventForEventType(event, postingState, clazz);
        }
    } else {
        // 发布事件
        subscriptionFound = postSingleEventForEventType(event, postingState, eventClass);
    }
    if (!subscriptionFound) {
        if (logNoSubscriberMessages) {
            Log.d(TAG, "No subscribers registered for event " + eventClass);
        }
        if (sendNoSubscriberEvent && eventClass != NoSubscriberEvent.class &&
                eventClass != SubscriberExceptionEvent.class) {
            post(new NoSubscriberEvent(this, event));
        }
    }
}
```

继续看发布事件的关键代码`postSingleEventForEventType()`。

```Java
private boolean postSingleEventForEventType(Object event, PostingThreadState postingState, Class<?> eventClass) {
    CopyOnWriteArrayList<Subscription> subscriptions;
    synchronized (this) {
        // 根据事件类型找出相关的订阅信息
        subscriptions = subscriptionsByEventType.get(eventClass);
    }
    if (subscriptions != null && !subscriptions.isEmpty()) {
        for (Subscription subscription : subscriptions) {
            postingState.event = event;
            postingState.subscription = subscription;
            boolean aborted = false;
            try {
                // 发布事件到具体的订阅者
                postToSubscription(subscription, event, postingState.isMainThread);
                aborted = postingState.canceled;
            } finally {
                postingState.event = null;
                postingState.subscription = null;
                postingState.canceled = false;
            }
            if (aborted) {
                break;
            }
        }
        return true;
    }
    return false;
}
```

如果该事件有订阅信息，则执行`postToSubscription()`。

```Java
private void postToSubscription(Subscription subscription, Object event, boolean isMainThread) {
    switch (subscription.subscriberMethod.threadMode) {
        // 订阅线程跟随发布线程
        case POSTING:
            // 订阅线程和发布线程相同，直接订阅
            invokeSubscriber(subscription, event);
            break;
        // 订阅线程为主线程
        case MAIN:
            if (isMainThread) {
                // 发布线程和订阅线程都是主线程，直接订阅
                invokeSubscriber(subscription, event);
            } else {
                // 发布线程不是主线程，订阅线程切换到主线程订阅
                mainThreadPoster.enqueue(subscription, event);
            }
            break;
        // 订阅线程为后台线程
        case BACKGROUND:
            if (isMainThread) {
                // 发布线程为主线程，切换到后台线程订阅
                backgroundPoster.enqueue(subscription, event);
            } else {
                // 发布线程不为主线程，直接订阅
                invokeSubscriber(subscription, event);
            }
            break;
        // 订阅线程为异步线程
        case ASYNC:
            // 使用线程池线程订阅
            asyncPoster.enqueue(subscription, event);
            break;
        default:
            throw new IllegalStateException("Unknown thread mode: " + subscription.subscriberMethod.threadMode);
    }
}
```

看到四种线程模式：

* `POSTING`：事件发布在什么线程，就在什么线程订阅。
* `MAIN`：无论事件在什么线程发布，都在主线程订阅。
* `BACKGROUND`：如果发布的线程不是主线程，则在该线程订阅，如果是主线程，则使用一个单独的后台线程订阅。
* `ASYNC`：在非主线程和发布线程中订阅。

继续看实现订阅者的方法`invokeSubscriber()`。

```java
void invokeSubscriber(Subscription subscription, Object event) {
    try {
        subscription.subscriberMethod.method.invoke(subscription.subscriber, event);
    } catch (InvocationTargetException e) {
        handleSubscriberException(subscription, event, e.getCause());
    } catch (IllegalAccessException e) {
        throw new IllegalStateException("Unexpected exception", e);
    }
}
```

订阅者接收到了事件，调用订阅方法，传入发布的事件作为参数，至此，事件发布过程就结束了。



## 反注册订阅者

```java
EventBus.getDefault().unregister(this);
```

```java
/** Unregisters the given subscriber from all event classes. */
public synchronized void unregister(Object subscriber) {
    List<Class<?>> subscribedTypes = typesBySubscriber.get(subscriber);
    if (subscribedTypes != null) {
        for (Class<?> eventType : subscribedTypes) {
            unsubscribeByEventType(subscriber, eventType);
        }
        typesBySubscriber.remove(subscriber);
    } else {
        Log.w(TAG, "Subscriber to unregister was not registered before: " + subscriber.getClass());
    }
}
```

这里根据订阅者拿到订阅事件类型 List，然后逐个取消订阅，调用`unsubscribeByEventType()`方法。

```java
/** Only updates subscriptionsByEventType, not typesBySubscriber! Caller must update typesBySubscriber. */
private void unsubscribeByEventType(Object subscriber, Class<?> eventType) {
    List<Subscription> subscriptions = subscriptionsByEventType.get(eventType);
    if (subscriptions != null) {
        int size = subscriptions.size();
        for (int i = 0; i < size; i++) {
            Subscription subscription = subscriptions.get(i);
            if (subscription.subscriber == subscriber) {
                subscription.active = false;
                subscriptions.remove(i);
                i--;
                size--;
            }
        }
    }
}
```

`subscriptionsByEventType`是存储事件类型对应订阅信息的 Map，代码逻辑非常清晰，找出某事件类型的订阅信息 List，遍历订阅信息，将要取消订阅的订阅者和订阅信息封装的订阅者比对，如果是同一个，则说明该订阅信息是将要失效的，于是将该订阅信息移除。