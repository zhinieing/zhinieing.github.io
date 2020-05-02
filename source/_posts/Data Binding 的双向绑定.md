---
title: Data Binding 的双向绑定
date: 2018-01-05 10:15:58
categories:
- 开源库
tags:
- Android
- library
---
>  DataBinding 支持双向绑定，能大大减少绑定 app 逻辑与 layout 文件的“胶水代码”。双向绑定，指的是将数据与界面绑定起来，当数据发生变化时会体现在界面上，反过来界面内容变化也会同步更新到数据上，使用 DataBinding 能轻松实现 MVVM 模式。

<!--more-->

## 初始化绑定

在初始化时我们会调用下面的代码：

```java
ActivityMainBinding binding = DataBindingUtil.setContentView(this, R.layout.activity_main);
binding.setUser(user);
```

进入`setUser`：

```java
public void setUser(User User) {
    this.mUser = User;
    synchronized(this) {
        this.mDirtyFlags |= 2L;
    }

    this.notifyPropertyChanged(1);
    super.requestRebind();
}
```

`mDirtyFlags`用于表示哪个属性发生变化，`notifyPropertyChanged(1)`实则为`notifyPropertyChanged(BR.user)`，顾名思义，是发出 user 数据变化的通知。看看`requestRebind`是干什么的：

```java
protected void requestRebind() {
    if (mContainingBinding != null) {
        mContainingBinding.requestRebind();
    } else {
        synchronized (this) {
            if (mPendingRebind) {
                return;
            }
            mPendingRebind = true;
        }
        if (USE_CHOREOGRAPHER) {
            mChoreographer.postFrameCallback(mFrameCallback);
        } else {
            mUIThreadHandler.post(mRebindRunnable);
        }
    }
}
```

这里根据 api 版本做了点不同的处理，API 16及以上的，会往`mChoreographer`发一个`mFrameCallback`；否则直接往 UI 线程发一个`mRebindRunnable`。其实这里俩个分支的结果基本一致，`mChoreographer`会在界面刷新时执行`mRebindRunnable`。

```java
private final Runnable mRebindRunnable = new Runnable() {
    @Override
    public void run() {
        synchronized (this) {
            mPendingRebind = false;
        }
        processReferenceQueue();

        if (VERSION.SDK_INT >= VERSION_CODES.KITKAT) {
            // Nested so that we don't get a lint warning in IntelliJ
            if (!mRoot.isAttachedToWindow()) {
                // Don't execute the pending bindings until the View
                // is attached again.
                mRoot.removeOnAttachStateChangeListener(ROOT_REATTACHED_LISTENER);
                mRoot.addOnAttachStateChangeListener(ROOT_REATTACHED_LISTENER);
                return;
            }
        }
        executePendingBindings();
    }
};
```

最终都会执行`executePendingBindings()`，继而调用`executeBindingsInternal()`方法。

```java
private void executeBindingsInternal() {
    if (mIsExecutingPendingBindings) {
        requestRebind();
        return;
    }
    if (!hasPendingBindings()) {
        return;
    }
    mIsExecutingPendingBindings = true;
    mRebindHalted = false;
    if (mRebindCallbacks != null) {
        mRebindCallbacks.notifyCallbacks(this, REBIND, null);

        // The onRebindListeners will change mPendingHalted
        if (mRebindHalted) {
            mRebindCallbacks.notifyCallbacks(this, HALTED, null);
        }
    }
    if (!mRebindHalted) {
        executeBindings();
        if (mRebindCallbacks != null) {
            mRebindCallbacks.notifyCallbacks(this, REBOUND, null);
        }
    }
    mIsExecutingPendingBindings = false;
}
```

`executeBindings`是一个抽象的方法，具体实现在编译时生成的`ActivityMainBinding`里。

```java
@Override
protected void executeBindings() {
    long dirtyFlags = 0;
    synchronized(this) {
        dirtyFlags = mDirtyFlags;
        mDirtyFlags = 0;
    }
    android.databinding.ObservableField<java.lang.String> userName = null;
    java.lang.String userNameGet = null;
    com.example.databindingdemo.User user = mUser;

    if ((dirtyFlags & 0x7L) != 0) {
        
            if (user != null) {
                // read user.name
                userName = user.getName();
            }
            updateRegistration(0, userName);

            if (userName != null) {
                // read user.name.get()
                userNameGet = userName.get();
            }
    }
    // batch finished
    if ((dirtyFlags & 0x7L) != 0) {
        // api target 1

        android.databinding.adapters.TextViewBindingAdapter.setText(this.button, userNameGet);
    }
}
```

这里面的代码比较简单，除了对界面进行赋值，还调用了`updateRegistration`方法。

```java
protected boolean updateRegistration(int localFieldId, Observable observable) {
    return updateRegistration(localFieldId, observable, CREATE_PROPERTY_LISTENER);
}
```

`updateRegistration`第三个参数传了`CREATE_PROPERTY_LISTENER`。

```java
private static final CreateWeakListener CREATE_PROPERTY_LISTENER = new CreateWeakListener() {
    @Override
    public WeakListener create(ViewDataBinding viewDataBinding, int localFieldId) {
       return new WeakPropertyListener(viewDataBinding, localFieldId).getListener();
    }
};

private static class WeakPropertyListener extends Observable.OnPropertyChangedCallback
            implements ObservableReference<Observable> {
    final WeakListener<Observable> mListener;

    public WeakPropertyListener(ViewDataBinding binder, int localFieldId) {
        mListener = new WeakListener<Observable>(binder, localFieldId, this);
    }

    // …… 

    @Override
    public void onPropertyChanged(Observable sender, int propertyId) {
        ViewDataBinding binder = mListener.getBinder();
        if (binder == null) {
            return;
        }
        Observable obj = mListener.getTarget();
        if (obj != sender) {
            return; // notification from the wrong object?
        }
        binder.handleFieldChange(mListener.mLocalFieldId, sender, propertyId);
    }
}

private static class WeakListener<T> extends WeakReference<ViewDataBinding> {
    private final ObservableReference<T> mObservable;
    protected final int mLocalFieldId;
    private T mTarget;

    public WeakListener(ViewDataBinding binder, int localFieldId,
            ObservableReference<T> observable) {
        super(binder, sReferenceQueue);
        mLocalFieldId = localFieldId;
        mObservable = observable;
    }

    // …… 
}
```

从上面知道`CREATE_PROPERTY_LISTENER`是一个`CreateWeakListener`对象，`CreateWeakListener.create()`能得到`WeakPropertyListener`，`WeakPropertyListener`内有变量`WeakListener`，`WeakListener`持有`ViewDataBinding`以及`Observable`。再看看`updateRegistration`方法。

```java
private boolean updateRegistration(int localFieldId, Object observable,
        CreateWeakListener listenerCreator) {
    if (observable == null) {
        return unregisterFrom(localFieldId);
    }
    WeakListener listener = mLocalFieldObservers[localFieldId];
    if (listener == null) {
        registerTo(localFieldId, observable, listenerCreator);
        return true;
    }
    if (listener.getTarget() == observable) {
        return false;//nothing to do, same object
    }
    unregisterFrom(localFieldId);
    registerTo(localFieldId, observable, listenerCreator);
    return true;
}
```

```java
protected void registerTo(int localFieldId, Object observable,
        CreateWeakListener listenerCreator) {
    if (observable == null) {
        return;
    }
    WeakListener listener = mLocalFieldObservers[localFieldId];
    if (listener == null) {
        listener = listenerCreator.create(this, localFieldId);
        mLocalFieldObservers[localFieldId] = listener;
    }
    listener.setTarget(observable);
}
```

`registerTo`把`CreateWeakListener`存储在`mLocalFieldObservers`里面。



![image-20180405000213738](../Data Binding 的双向绑定/image-20180405000213738.png)

这样一来 View 和 VM 的联系就通过`ViewDatabinding`建立起来了。View 内有`ViewDatabinding`，而`ViewDatabinding`里持有各个 View 的引用。`ViewDataBindin`g有 VM 的变量，而 VM 内的`PropertyChangeRegistry`监听实则为`WeakPropertyListener`，`WeakListener`能获取到`ViewDatabinding`。



## VM 变化如何通知 View

要达到 VM 变化时自动绑定到 View 上，有下面俩种方式：

* 继承自 BaseObservable，在 getter 上增加`@Bindable`注解，在 setter 里增加代码`notifyPropertyChanged(BR.xxx)`。
* 无需继承，需要将属性替换为 Observable 类，例如`ObservableInt、ObservableField`等。

这两种本质上都是一样的。在第二种方式中，当属性发生变化时，会调用`notifyChange`，而`notifyChange`与`notifyPropertyChanged`做的事情都是一样的，都是调用`mCallbacks.notifyCallbacks`去通知。

```Java
public void notifyChange() {
    synchronized (this) {
        if (mCallbacks == null) {
            return;
        }
    }
    mCallbacks.notifyCallbacks(this, 0, null);
}

public void notifyPropertyChanged(int fieldId) {
    synchronized (this) {
        if (mCallbacks == null) {
            return;
        }
    }
    mCallbacks.notifyCallbacks(this, fieldId, null);
}
```



## View 的变化如何同步到 VM

DataBinding 在旧版本中是不支持这个功能的，后来才完善了这个功能。

```java
android:text="@={user.name}"
```

在使用双向绑定后，可以发现在`executeBindings`里多了一点代码：

```java
@Override
protected void executeBindings() {
    // …… 
    if ((dirtyFlags & 0x4L) != 0) {
        // api target 1
        android.databinding.adapters.TextViewBindingAdapter.setTextWatcher(this.button, (android.databinding.adapters.TextViewBindingAdapter.BeforeTextChanged)null, (android.databinding.adapters.TextViewBindingAdapter.OnTextChanged)null, (android.databinding.adapters.TextViewBindingAdapter.AfterTextChanged)null, buttonandroidTextAttrChanged);
    }
}
```

在这个方法里调用了`setTextWatcher`去监听 Button 的`TextWatcher`。

```java
@BindingAdapter(value = {"android:beforeTextChanged", "android:onTextChanged",
        "android:afterTextChanged", "android:textAttrChanged"}, requireAll = false)
public static void setTextWatcher(TextView view, final BeforeTextChanged before,
        final OnTextChanged on, final AfterTextChanged after,
        final InverseBindingListener textAttrChanged) {
    final TextWatcher newValue;
    if (before == null && after == null && on == null && textAttrChanged == null) {
        newValue = null;
    } else {
        newValue = new TextWatcher() {
            // …… 
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                if (textAttrChanged != null) {
                    textAttrChanged.onChange();
                }
            }
            // …...
        };
    }
    // …...
    if (newValue != null) {
        view.addTextChangedListener(newValue);
    }
}
```

当 View 发生变化时，会调`textAttrChanged`的`onChange`方法。

```java
// Inverse Binding Event Handlers
private android.databinding.InverseBindingListener buttonandroidTextAttrChanged = new android.databinding.InverseBindingListener() {
    @Override
    public void onChange() {
        // Inverse of user.name.get()
        //         is user.name.set((java.lang.String) callbackArg_0)
        java.lang.String callbackArg_0 = android.databinding.adapters.TextViewBindingAdapter.getTextString(button);
        // localize variables for thread safety
        // user.name
        android.databinding.ObservableField<java.lang.String> userName = null;
        // user.name != null
        boolean userNameJavaLangObjectNull = false;
        // user != null
        boolean userJavaLangObjectNull = false;
        // user
        com.example.databindingdemo.User user = mUser;
        // user.name.get()
        java.lang.String userNameGet = null;

        userJavaLangObjectNull = (user) != (null);
        if (userJavaLangObjectNull) {

            userName = user.getName();

            userNameJavaLangObjectNull = (userName) != (null);
            if (userNameJavaLangObjectNull) {
                userName.set(((java.lang.String) (callbackArg_0)));
            }
        }
    }
};
```

在`onChange`回调里，将变动后的值赋值到 VM 上。这样，View 的变化就自动同步到 VM 上了。



## 双向绑定的问题及解决方式

1. 死循环绑定：因为数据源改变会通知 View 刷新，而 View 改变又会通知数据源刷新，这样一直循环往复，就形成了死循环绑定。 

   解决方法：在处理双向绑定的业务逻辑时，要对新旧数据进行比较，只处理新旧数据不一样的数据，对于新旧数据一样的数据作 return 处理，通过这种方式来避免死循环绑定。

2. 数据源中的数据有时需要经过转换才能在 View 中展示，而 View 中展示的内容也需要经过转换才能绑定到对应的数据源上。

   解决方法：使用`@InverseMethod`定义转换方法，在布局文件中使用。
