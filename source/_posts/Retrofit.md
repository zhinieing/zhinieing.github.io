---
title: Retrofit
date: 2018-01-16 13:45:52
categories:
- 开源库
tags:
- Android
- library
---
> Retrofit 是一个 RESTful 的 HTTP 网络请求框架的封装。网络请求的工作本质上是 OkHttp 完成，而 Retrofit 仅负责网络请求接口的封装。

<!--more-->

## Retrofit 的本质流程

![](../Retrofit/944365-72f373fbbb960b69.png)

具体过程：

1. 通过解析网络请求接口的注解、配置、网络请求参数
2. 通过动态代理生成网络请求对象
3. 通过网络请求适配器对网络请求对象进行平台适配
4. 通过网络请求执行器发送网络请求
5. 通过数据转换器解析服务器返回的数据
6. 通过回调执行器切换线程
7. 用户在主线程处理返回结果



下面介绍上面提到的几个角色

![](../Retrofit/944365-5f4b1f44be83e554.png)




## 源码分析

**Retrofit 的使用步骤：**

1. 创建 Retrofi 实例
2. 创建网络请求接口实例并配置网络请求参数
3. 发送网络请求
4. 处理服务器返回的数据



### 创建 Retrofit 实例

![mage-20180402114526](../Retrofit/image-201804021145261.png)

**步骤1**

```java
<-- Retrofit类 -->
public final class Retrofit {

    private final Map<Method, ServiceMethod> serviceMethodCache = new LinkedHashMap<>();
    // 网络请求配置对象（对网络请求接口中方法注解进行解析后得到的对象）
    // 作用：存储网络请求相关的配置，如网络请求的方法、数据转换器、网络请求适配器、网络请求工厂、基地址等

    private final HttpUrl baseUrl;
    // 网络请求的url地址

    private final okhttp3.Call.Factory callFactory;
    // 网络请求器的工厂
    // 作用：生产网络请求器（Call）
    // Retrofit是默认使用okhttp

    private final List<CallAdapter.Factory> adapterFactories;
    // 网络请求适配器工厂的集合
    // 作用：放置网络请求适配器工厂
    // 网络请求适配器工厂作用：生产网络请求适配器（CallAdapter）
    // 下面会详细说明


    private final List<Converter.Factory> converterFactories;
    // 数据转换器工厂的集合
    // 作用：放置数据转换器工厂
    // 数据转换器工厂作用：生产数据转换器（converter）

    private final Executor callbackExecutor;
    // 回调方法执行器

    private final boolean validateEagerly; 
    // 标志位
    // 作用：是否提前对业务接口中的注解进行验证转换的标志位


    <-- Retrofit类的构造函数 -->
    Retrofit(okhttp3.Call.Factory callFactory, HttpUrl baseUrl,  
      List<Converter.Factory> converterFactories, List<CallAdapter.Factory> adapterFactories, Executor callbackExecutor, boolean validateEagerly) {  
        this.callFactory = callFactory;  
        this.baseUrl = baseUrl;  
        this.converterFactories = unmodifiableList(converterFactories); 
        this.adapterFactories = unmodifiableList(adapterFactories);   
        // unmodifiableList(list)近似于UnmodifiableList<E>(list)
        // 作用：创建的新对象能够对list数据进行访问，但不可通过该对象对list集合中的元素进行修改
        this.callbackExecutor = callbackExecutor;  
        this.validateEagerly = validateEagerly;  
        ...
        // 仅贴出关键代码
    }
}
```

成功建立一个 Retrofit 对象的标准：配置好 Retrofit 类里的成员变量

* `serviceMethod`：包含所有网络请求信息的对象
* `baseUrl`：网络请求的url地址
* `callFactory`：网络请求工厂
* `adapterFactories`：网络请求适配器工厂的集合
* `converterFactories`：数据转换器工厂的集合
* `callbackExecutor`：回调方法执行器



**`CallAdapter`详细介绍**

* 定义：网络请求执行器（Call）的适配器

> Call 在 Retrofit 里默认是`OkHttpCall`
>
> 在 Retrofit 中提供了四种`CallAdapterFactory`： `ExecutorCallAdapterFactory`（默认）、`GuavaCallAdapterFactory`、`Java8CallAdapterFactory`、`RxJavaCallAdapterFactory`

* 作用：将默认的网络请求执行器（`OkHttpCall`）转换成适合被不同平台来调用的网络请求执行器形式

> 一开始`Retrofit`只打算利用`OkHttpCall`通过`ExecutorCallbackCall`切换线程；但后来发现使用`Rxjava`更加方便（不需要Handler来切换线程）。想要实现`Rxjava`的情况，那就得使用`RxJavaCallAdapterFactoryCallAdapter`将`OkHttpCall`转换成`Rxjava(Scheduler)`：

```java
// 把response封装成rxjava的Observeble，然后进行流式操作
Retrofit.Builder.addCallAdapterFactory(newRxJavaCallAdapterFactory().create()); 
```



**步骤2**

```Java
<-- Builder类-->
public static final class Builder {
    private Platform platform;
    private okhttp3.Call.Factory callFactory;
    private HttpUrl baseUrl;
    private List<Converter.Factory> converterFactories = new ArrayList<>();
    private List<CallAdapter.Factory> adapterFactories = new ArrayList<>();
    private Executor callbackExecutor;
    private boolean validateEagerly;

    // 从上面可以发现， Builder类的成员变量与Retrofit类的成员变量是对应的
    // 所以Retrofit类的成员变量基本上是通过Builder类进行配置
    // 开始看步骤1

    <-- 步骤1 -->
    // Builder的构造方法（无参）
    public Builder() {
      this(Platform.get());
    // 用this调用自己的有参构造方法public Builder(Platform platform) ->>步骤5（看完步骤2、3、4再看）
    // 并通过调用Platform.get（）传入了Platform对象
    // 继续看Platform.get()方法 ->>步骤2
    // 记得最后继续看步骤5的Builder有参构造方法
    }
    ...
    }

    <-- 步骤2 -->
    class Platform {

    private static final Platform PLATFORM = findPlatform();
    // 将findPlatform()赋给静态变量

    static Platform get() {
    return PLATFORM;    
    // 返回静态变量PLATFORM，即findPlatform() ->>步骤3
    }

    <-- 步骤3 -->
    private static Platform findPlatform() {
    try {

      Class.forName("android.os.Build");
      // Class.forName(xxx.xx.xx)的作用：要求JVM查找并加载指定的类（即JVM会执行该类的静态代码段）
      if (Build.VERSION.SDK_INT != 0) {
        return new Android(); 
        // 此处表示：如果是Android平台，就创建并返回一个Android对象 ->>步骤4
      }
    } catch (ClassNotFoundException ignored) {
    }

    try {
      // 支持Java平台
      Class.forName("java.util.Optional");
      return new Java8();
    } catch (ClassNotFoundException ignored) {
    }

    try {
      // 支持iOS平台
      Class.forName("org.robovm.apple.foundation.NSObject");
      return new IOS();
    } catch (ClassNotFoundException ignored) {
    }

    // 从上面看出：Retrofit2.0支持3个平台：Android平台、Java平台、IOS平台
    // 最后返回一个Platform对象（指定了Android平台）给Builder的有参构造方法public Builder(Platform platform)  --> 步骤5
    // 说明Builder指定了运行平台为Android
    return new Platform();
    }
    ...
    }

    <-- 步骤4 -->
    // 用于接收服务器返回数据后进行线程切换在主线程显示结果

    static class Android extends Platform {

    @Override
      CallAdapter.Factory defaultCallAdapterFactory(Executor callbackExecutor) {

      return new ExecutorCallAdapterFactory(callbackExecutor);
    // 创建默认的网络请求适配器工厂
    // 该默认工厂生产的 adapter 会使得Call在异步调用时在指定的 Executor 上执行回调
    // 在Retrofit中提供了四种CallAdapterFactory： ExecutorCallAdapterFactory（默认）、GuavaCallAdapterFactory、Java8CallAdapterFactory、RxJavaCallAdapterFactory
    // 采用了策略模式

    }

    @Override 
      public Executor defaultCallbackExecutor() {
      // 返回一个默认的回调方法执行器
      // 该执行器作用：切换线程（子->>主线程），并在主线程（UI线程）中执行回调方法
      return new MainThreadExecutor();
    }

    static class MainThreadExecutor implements Executor {

      private final Handler handler = new Handler(Looper.getMainLooper());
      // 获取与Android 主线程绑定的Handler 

      @Override 
      public void execute(Runnable r) {


        handler.post(r);
        // 该Handler是上面获取的与Android 主线程绑定的Handler 
        // 在UI线程进行对网络请求返回数据处理等操作。
      }
    }

    // 切换线程的流程：
    // 1. 回调ExecutorCallAdapterFactory生成了一个ExecutorCallbackCall对象
    //2. 通过调用ExecutorCallbackCall.enqueue(CallBack)从而调用MainThreadExecutor的execute()通过handler切换到主线程
    }

    // 下面继续看步骤5的Builder有参构造方法
    <-- 步骤5 -->
    //  Builder类的构造函数2（有参）
    public  Builder(Platform platform) {

    // 接收Platform对象（Android平台）
      this.platform = platform;

    // 通过传入BuiltInConverters()对象配置数据转换器工厂（converterFactories）

    // converterFactories是一个存放数据转换器Converter.Factory的数组
    // 配置converterFactories即配置里面的数据转换器
      converterFactories.add(new BuiltInConverters());

    // BuiltInConverters是一个内置的数据转换器工厂（继承Converter.Factory类）
    // new BuiltInConverters()是为了初始化数据转换器
    }
}
```

Builder 设置了默认的

- 平台类型对象：Android
- 网络请求适配器工厂：`CallAdapterFactory`
- 数据转换器工厂： `converterFactory`
- 回调执行器：`callbackExecutor`



**步骤3**

```Java
<-- 步骤1 -->
public Builder baseUrl(String baseUrl) {

  // 把String类型的url参数转化为适合OKhttp的HttpUrl类型
  HttpUrl httpUrl = HttpUrl.parse(baseUrl);     

// 最终返回带httpUrl类型参数的baseUrl（）
// 下面继续看baseUrl(httpUrl) ->> 步骤2
  return baseUrl(httpUrl);
}


<-- 步骤2 -->
public Builder baseUrl(HttpUrl baseUrl) {

  //把URL参数分割成几个路径碎片
  List<String> pathSegments = baseUrl.pathSegments();   

  // 检测最后一个碎片来检查URL参数是不是以"/"结尾
  // 不是就抛出异常    
  if (!"".equals(pathSegments.get(pathSegments.size() - 1))) {
    throw new IllegalArgumentException("baseUrl must end in /: " + baseUrl);
  }     
  this.baseUrl = baseUrl;
  return this;
}
```

`baseUrl()`用于配置 Retrofit 类的网络请求 url 地址



**步骤4**

```Java
public final class GsonConverterFactory extends Converter.Factory {

<-- 步骤1 -->
  public static GsonConverterFactory create() {
    // 创建一个Gson对象
    return create(new Gson()); ->>步骤2
  }

<-- 步骤2 -->
  public static GsonConverterFactory create(Gson gson) {
    // 创建了一个含有Gson对象实例的GsonConverterFactory
    return new GsonConverterFactory(gson); ->>步骤3
  }

  private final Gson gson;

<-- 步骤3 -->
  private GsonConverterFactory(Gson gson) {
    if (gson == null) throw new NullPointerException("gson == null");
    this.gson = gson;
  }
}
```

```java
// 将上面创建的GsonConverterFactory放入到 converterFactories数组
// 在第二步放入一个内置的数据转换器工厂BuiltInConverters(）后又放入了一个GsonConverterFactory
public Builder addConverterFactory(Converter.Factory factory) {
  converterFactories.add(checkNotNull(factory, "factory == null"));
  return this;
}
```

创建一个含有 Gson 对象实例的`GsonConverterFactory`并放入到数据转换器工厂`converterFactories`里



**步骤5**

```Java
public Retrofit build() {

<--  配置网络请求执行器（callFactory）-->
  okhttp3.Call.Factory callFactory = this.callFactory;
  // 如果没指定，则默认使用okhttp
  // 所以Retrofit默认使用okhttp进行网络请求
  if (callFactory == null) {
    callFactory = new OkHttpClient();
  }

<--  配置回调方法执行器（callbackExecutor）-->
  Executor callbackExecutor = this.callbackExecutor;
  // 如果没指定，则默认使用Platform检测环境时的默认callbackExecutor
  // 即Android默认的callbackExecutor
  if (callbackExecutor == null) {
    callbackExecutor = platform.defaultCallbackExecutor();
  }

<--  配置网络请求适配器工厂（CallAdapterFactory）-->
  List<CallAdapter.Factory> adapterFactories = new ArrayList<>(this.adapterFactories);
  // 向该集合中添加了步骤2中创建的CallAdapter.Factory请求适配器（添加在集合器末尾）
  adapterFactories.add(platform.defaultCallAdapterFactory(callbackExecutor));
// 请求适配器工厂集合存储顺序：自定义1适配器工厂、自定义2适配器工厂...默认适配器工厂（ExecutorCallAdapterFactory）

<--  配置数据转换器工厂：converterFactory -->
  // 在步骤2中已经添加了内置的数据转换器BuiltInConverters(）（添加到集合器的首位）
  // 在步骤4中又插入了一个Gson的转换器 - GsonConverterFactory（添加到集合器的首二位）
  List<Converter.Factory> converterFactories = new ArrayList<>(this.converterFactories);
  // 数据转换器工厂集合存储的是：默认数据转换器工厂（ BuiltInConverters）、自定义1数据转换器工厂（GsonConverterFactory）、自定义2数据转换器工厂....

// 注：
//1. 获取合适的网络请求适配器和数据转换器都是从adapterFactories和converterFactories集合的首位-末位开始遍历
// 因此集合中的工厂位置越靠前就拥有越高的使用权限

  // 最终返回一个Retrofit的对象，并传入上述已经配置好的成员变量
  return new Retrofit(callFactory, baseUrl, converterFactories, adapterFactories,
      callbackExecutor, validateEagerly);
}
```

成功创建了 Retrofit 的实例



### 创建网络请求接口的实例

```java
retrofit.create(XXX.class);
```

```Java
public <T> T create(final Class<T> service) {
    if (validateEagerly) {  
        // 判断是否需要提前验证
        eagerlyValidateMethods(service); 
        // 具体方法作用：
        // 1. 给接口中每个方法的注解进行解析并得到一个ServiceMethod对象
        // 2. 以Method为键将该对象存入LinkedHashMap集合中
        // 特别注意：如果不是提前验证则进行动态解析对应方法（下面会详细说明），得到一个ServiceMethod对象，最后存入到LinkedHashMap集合中，类似延迟加载（默认）
    }  


        // 创建了网络请求接口的动态代理对象，即通过动态代理创建网络请求接口的实例 （并最终返回）
        // 该动态代理是为了拿到网络请求接口实例上所有注解
    return (T) Proxy.newProxyInstance(
          service.getClassLoader(),      // 动态生成接口的实现类 
          new Class<?>[] { service },    // 动态创建实例
          new InvocationHandler() {     // 将代理类的实现交给 InvocationHandler类作为具体的实现（下面会解释）
          private final Platform platform = Platform.get();

         // 在 InvocationHandler类的invoke（）实现中，除了执行真正的逻辑（如再次转发给真正的实现类对象），还可以进行一些有用的操作
         // 如统计执行时间、进行初始化和清理、对接口调用进行检查等。
          @Override 
           public Object invoke(Object proxy, Method method, Object... args)
              throws Throwable {
          
            // 下面会详细介绍 invoke（）的实现
            // 即下面三行代码
            ServiceMethod serviceMethod = loadServiceMethod(method);     
            OkHttpCall okHttpCall = new OkHttpCall<>(serviceMethod, args);
            return serviceMethod.callAdapter.adapt(okHttpCall);
          }
        });
  }

// 特别注意
// return (T) roxy.newProxyInstance(ClassLoader loader, Class<?>[] interfaces,  InvocationHandler invocationHandler)
// 可以解读为：getProxyClass(loader, interfaces) .getConstructor(InvocationHandler.class).newInstance(invocationHandler);
// 即通过动态生成的代理类，调用interfaces接口的方法实际上是通过调用InvocationHandler对象的invoke（）来完成指定的功能
// 先记住结论，在讲解步骤4的时候会再次详细说明


<-- 关注点1：eagerlyValidateMethods（） -->
	private void eagerlyValidateMethods(Class<?> service) {  
        Platform platform = Platform.get();  
        for (Method method : service.getDeclaredMethods()) {  
        if (!platform.isDefaultMethod(method)) {  loadServiceMethod(method); } 
          // 将传入的ServiceMethod对象加入LinkedHashMap<Method, ServiceMethod>集合
         // 使用LinkedHashMap集合的好处：lruEntries.values().iterator().next()获取到的是集合最不经常用到的元素，提供了一种Lru算法的实现
    }  
}
```

> 创建网络接口实例用了外观模式 & 代理模式

通过代理模式中的动态代理模式，动态生成网络请求接口的代理类，并将代理类的实例创建交给`InvocationHandler类` 作为具体的实现，并最终返回一个动态代理对象。

使用动态代理的好处：

* 当`NetService`对象调用`getCall（）`接口中方法时会进行拦截，调用都会集中转发到`InvocationHandler#invoke（）`，可集中进行处理
* 获得网络请求接口实例上的所有注解
* 更方便封装`ServiceMethod`



```Java
new InvocationHandler() {   
    private final Platform platform = Platform.get();
    
    @Override 
    public Object invoke(Object proxy, Method method, Object... args) throws Throwable{
        // 将详细介绍下面代码
        // 关注点1
        // 作用：读取网络请求接口里的方法，并根据前面配置好的属性配置serviceMethod对象
        ServiceMethod serviceMethod = loadServiceMethod(method);     

        // 关注点2
        // 作用：根据配置好的serviceMethod对象创建okHttpCall对象 
        OkHttpCall okHttpCall = new OkHttpCall<>(serviceMethod, args);

        // 关注点3
        // 作用：调用OkHttp，并根据okHttpCall返回rejava的Observe对象或者返回Call
        return serviceMethod.callAdapter.adapt(okHttpCall);
    }
}
```

**Retrofit 采用了外观模式统一调用创建网络请求接口实例和网络请求参数配置的方法，具体细节是:**

* 动态创建网络请求接口的实例**（代理模式 - 动态代理）**
* 创建 `serviceMethod` 对象**（建造者模式 & 单例模式（缓存机制））**
* 对 `serviceMethod` 对象进行网络请求参数配置：通过解析网络请求接口方法的参数、返回值和注解类型，从 Retrofit 对象中获取对应的网络请求的 url 地址、网络请求执行器、网络请求适配器 & 数据转换器。**（策略模式）**
* 对 `serviceMethod` 对象加入线程切换的操作，便于接收数据后通过 Handler 从子线程切换到主线程从而对返回数据结果进行处理**（装饰模式）**
* 最终创建并返回一个`OkHttpCall`类型的网络请求对象



### 执行网络请求

* `Retrofit`默认使用`OkHttp`，即`OkHttpCall类`
* `OkHttpCall`提供了两种网络请求方式：
  1. 同步请求：`OkHttpCall.execute()`
  2. 异步请求：`OkHttpCall.enqueue()`



**同步请求**

* **步骤1：**对网络请求接口的方法中的每个参数利用对应`ParameterHandler`进行解析，再根据`ServiceMethod`对象创建一个`OkHttp`的`Request`对象
* **步骤2：**使用`OkHttp`的`Request`发送网络请求；
* **步骤3：**对返回的数据使用之前设置的数据转换器（`GsonConverterFactory`）解析返回的数据，最终得到一个`Response<T>`对象



**异步请求**

* **步骤1：**对网络请求接口的方法中的每个参数利用对应`ParameterHandler`进行解析，再根据`ServiceMethod`对象创建一个`OkHttp`的`Request`对象
* **步骤2：**使用`OkHttp`的`Request`发送网络请求；
* **步骤3：**对返回的数据使用之前设置的数据转换器（`GsonConverterFactory`）解析返回的数据，最终得到一个`Response<T>`对象
* **步骤4：**进行线程切换从而在主线程处理返回的数据结果



## 总结

Retrofit 本质上是一个`RESTful`的 HTTP 网络请求框架的封装，即通过大量的设计模式封装了 `OkHttp` ，使得简洁易用。具体过程如下：

1. Retrofit 将 Http 请求抽象成 Java 接口
2. 在接口里用注解描述和配置网络请求参数
3. 用动态代理的方式，动态将网络请求接口的注解解析成 HTTP 请求
4. 最后执行 HTTP 请求