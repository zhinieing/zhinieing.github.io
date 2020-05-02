---
title: Android 应用架构
date: 2018-04-08 10:41:33
categories:
- 程序设计
tags:
- Android
- MVVM
- library
---
> 关于 Android 架构的讨论，MVC、MVP 和 MVVM 不绝于耳，后面又有模块化和插件化。下面主要对比前三者的异同，以及具体介绍 Google 推出的 Architecture Components 开源库。

<!--more-->

先上结论：

* MVC：Model-View-Controller，经典模式，很容易理解，主要缺点有两个：
  1. View 对 Model 的依赖，会导致 View 也包含了业务逻辑
  2. Controller 会变得很厚很复杂
* MVP：Model-View-Presenter，MVC 的一个演变模式，将 Controller 换成了 Presenter，主要为了解决上述第一个缺点，将 View 和 Model 解耦，不过第二个缺点依然没有解决。
* MVVM：Model-View-ViewModel，是对 MVP 的一个优化模式，采用了双向绑定：View 的变动，自动反映在 ViewModel，反之亦然。



## MVC

![image-20180404194544857](../Android 应用架构/image-20180404194544857.png)

我们平时写的 Demo 都是 MVC，controller 就是我们的 activity，model（数据提供者）就是读取数据库，网络请求这些我们一般有专门的类处理，View 一般用自定义控件。

在实际开发中，我们的 activity 代码其实是越来越多，model 和 controller 根本没有分离，控件也需要关系数据和业务，才能知道自己怎么展示。



## MVP

![image-20180404194626257](../Android 应用架构/image-20180404194626257.png)



![image-20180404140906305](../Android 应用架构/image-20180404140906305.png)

上图可以看出，从 MVC 中 View 被拆成了 Presenter 和 View，真正实现了逻辑处理和 View 的分离。

### Model 层

```java
/**
定义业务接口
*/
public interface IUserBiz
{
    public void login(String username, String password, OnLoginListener loginListener);
}
/**
结果回调接口
*/
public interface OnLoginListener
{
    void loginSuccess(User user);
    void loginFailed();
}
/**
具体Model的实现
*/
public class UserBiz implements IUserBiz
{
    @Override
    public void login(final String username, final String password, final OnLoginListener loginListener)
    {
        //模拟子线程耗时操作
        new Thread()
        {
            @Override
            public void run()
            {
                try
                {
                    Thread.sleep(2000);
                } catch (InterruptedException e)
                {
                    e.printStackTrace();
                }
                //模拟登录成功
                if ("zhy".equals(username) && "123".equals(password))
                {
                    User user = new User();
                    user.setUsername(username);
                    user.setPassword(password);
                    loginListener.loginSuccess(user);
                } else
                {
                    loginListener.loginFailed();
                }
            }
        }.start();
    }
}
```

### View 层

View 层是以接口的形式定义，我们不关心数据，不关心逻辑处理！只关心和用户的交互。

```java
public interface IUserLoginView
{
    String getUserName();
    String getPassword();
    void clearUserName();
    void clearPassword();
    void showLoading();
    void hideLoading();
    void toMainActivity(User user);
    void showFailedError();
}
```

然后 Activity 实现这个这个接口：

```java
public class UserLoginActivity extends ActionBarActivity implements IUserLoginView
{
    private EditText mEtUsername, mEtPassword;
    private Button mBtnLogin, mBtnClear;
    private ProgressBar mPbLoading;
    private UserLoginPresenter mUserLoginPresenter = new UserLoginPresenter(this);
    @Override
    protected void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_user_login);
        initViews();
    }
    private void initViews()
    {
        mEtUsername = (EditText) findViewById(R.id.id_et_username);
        mEtPassword = (EditText) findViewById(R.id.id_et_password);
        mBtnClear = (Button) findViewById(R.id.id_btn_clear);
        mBtnLogin = (Button) findViewById(R.id.id_btn_login);
        mPbLoading = (ProgressBar) findViewById(R.id.id_pb_loading);
        mBtnLogin.setOnClickListener(new View.OnClickListener()
        {
            @Override
            public void onClick(View v)
            {
                mUserLoginPresenter.login();
            }
        });
        mBtnClear.setOnClickListener(new View.OnClickListener()
        {
            @Override
            public void onClick(View v)
            {
                mUserLoginPresenter.clear();
            }
        });
    }
    @Override
    public String getUserName()
    {
        return mEtUsername.getText().toString();
    }
    @Override
    public String getPassword()
    {
        return mEtPassword.getText().toString();
    }
    @Override
    public void clearUserName()
    {
        mEtUsername.setText("");
    }
    @Override
    public void clearPassword()
    {
        mEtPassword.setText("");
    }
    @Override
    public void showLoading()
    {
        mPbLoading.setVisibility(View.VISIBLE);
    }
    @Override
    public void hideLoading()
    {
        mPbLoading.setVisibility(View.GONE);
    }
    @Override
    public void toMainActivity(User user)
    {
        Toast.makeText(this, user.getUsername() +
                " login success , to MainActivity", Toast.LENGTH_SHORT).show();
    }
    @Override
    public void showFailedError()
    {
        Toast.makeText(this,
                "login failed", Toast.LENGTH_SHORT).show();
    }
}
```

### Presenter 层

Presenter 的作用就是从 View 层获取用户的输入，传递到 Model 层进行处理，然后回调给 View 层，输出给用户。

```java
public class UserLoginPresenter
{
    private IUserBiz userBiz;
    private IUserLoginView userLoginView;
    private Handler mHandler = new Handler();
//Presenter必须要能拿到View和Model的实现类
    public UserLoginPresenter(IUserLoginView userLoginView)
    {
        this.userLoginView = userLoginView;
        this.userBiz = new UserBiz();
    }
    public void login()
    {
        userLoginView.showLoading();
        userBiz.login(userLoginView.getUserName(), userLoginView.getPassword(), new OnLoginListener()
        {
            @Override
            public void loginSuccess(final User user)
            {
                //需要在UI线程执行
                mHandler.post(new Runnable()
                {
                    @Override
                    public void run()
                    {
                        userLoginView.toMainActivity(user);
                        userLoginView.hideLoading();
                    }
                });
            }
            @Override
            public void loginFailed()
            {
                //需要在UI线程执行
                mHandler.post(new Runnable()
                {
                    @Override
                    public void run()
                    {
                        userLoginView.showFailedError();
                        userLoginView.hideLoading();
                    }
                });
            }
        });
    }
    public void clear()
    {
        userLoginView.clearUserName();
        userLoginView.clearPassword();
    }
}
```

MVP 成功解决了 MVC 的第一个缺点，但是逻辑处理还是杂糅在 Activity。MVC 到 MVP 简单说，就是增加了一个接口降低一层耦合。但这样会因为在 presenter 中持有 View 接口的引用导致了 Activity 的内存泄露，解决方法可以用如下办法：

* 在 presenter 中声明一个 onDestroy() 方法，在这个方法中将 View 接口对象置为 null，然后在 presenter 中凡是使用到 View 接口的地方，都判断一下是否为空。
* 在 activity 的 onDestroy() 方法中调用 presenter.onDestroy()，同时也将 activity 持有的 presenter 置空。

## MVVM

![image-20180404194649235](../Android 应用架构/image-20180404194649235.png)

MVVM(Model-View-ViewModel)：MVVM 和 MVP 的区别其实不大，只不过是把 presenter 层换成了 ViewModel 层。它采用的是数据绑定（data-binding）方式，而且是双向绑定：View 绑定到 ViewModel，然后执行一些命令在向它请求一个动作。而反过来，ViewModel 跟 Model通讯，告诉它更新来响应 UI。



### 常见的构建原则

* 关注点分离：一个常见的错误是在 Activity 和 Fragment 中编写所有的代码。任何和 UI 或者操作系统交互无关的代码都尽量不要出现在这些类中，尽量保持这些类的精简会帮助你避免很多和生命周期相关的问题。最好减少对它们的依赖以提供一个稳定的用户体验。
* 通过 Model 驱动 UI，最好是持久化的 Model。最好使用持久化的数据有两个原因：a. 如果系统销毁应用释放资源，用户也不用担心丢失数据； b. 即使网络连接不可靠或者断网，应用仍将继续运行。Model 是负责处理应用数据的组件，Model 独立运行于应用中的 View 和应用程序中的其他组件，因此 Model 和其他应用程序组件的生命周期无关。基于 Model 构建的应用程序，其管理数据的职责明确，所以更容易测试，而且稳定性更高。



### Architecture Components 带来的 MVVM 架构

Architecture Components 包含了一系列的组件，这些组件能帮助你设计出稳健的，可测试的，架构清晰的 app。

![image-20180404201749666](../Android 应用架构/image-20180404201749666.png)

* **Lifecycle**：它是一个持有 Activity/Fragment 生命周期状态信息的类，并且允许其他对象观察此状态。
* **LiveData**：一个数据持有类，持有数据并且这个数据可以被观察被监听，和其他 Observer 不同的是，它是和 Lifecycle 是绑定的，在生命周期内使用有效，减少内存泄露和引用问题。
* **ViewModel**：用于管理数据，它持有 LiveData。处理数据持久化、存取等具体逻辑，相当于 MVP 中的 Presenter。同时是与 Lifecycle 绑定的，使用者无需担心生命周期。
* **Room**：Google 推出的一个 Sqlite ORM 库，使用注解，极大简化数据库的操作。
* **Paging**：分批加载，能够从指定数据源分批加载数据，能配合`PagedListAdapter`、RecylerView 实现分页加载，并且实现了 ==diff机制==，能够局部更新。



#### 快速了解

1. 创建一个 ViewModel，持有一个 LiveData

   ```java
   public class MyViewModel extends ViewModel {

      // 创建可变LiveData
      private MutableLiveData<UserDTO> mUserDTO;

       public MutableLiveData<String> getCurrentUser() {
           if (mUserDTO == null) {
               mUserDTO = loadData()
           }
           return mUserDTO;
       }

       // 获取数据
       private MutableLiveData<UserDTO> loadData(){}
      
   }
   ```

2. 使用 ViewModel，观察其持有的 LiveData

   ```java
   public class NameActivity extends AppCompatActivity {

       private NameViewModel mModel;

       @Override
       protected void onCreate(Bundle savedInstanceState) {
           super.onCreate(savedInstanceState);
   		
           // 获取ViewModel，绑定当前的activity的生命周期
           mModel = ViewModelProviders.of(this).get(MyViewModel.class);

           //创建观察者
           final Observer<UserDTO> userObserver = new Observer<UserDTO>() {
               @Override
               public void onChanged(@Nullable final UserDTO user) {
                   // 更新UI
                   mNameTextView.setText(user.TrueName);
               }
           };

           // 绑定观察者,和当前activity的生命周期
           mModel.getCurrentUser().observe(this, userObserver);
       }
   }
   ```

   ​

### 详解 Lifecycle、LiveData、ViewModel

#### Lifecycle

Lifecycle 主要包含三个部分：

* `Lifecycle`抽象类：这个类持有了 activity、fragment 等组件的生命周期状态，是一个被观察的对象，拥有`addObserver`和`removeObserver`等方法。 
* `LifecycleOwner`接口：接口的实现者默认持有一个 Lifecycle，外接可以调用`getLifecycle`获取到它持有的 Lifecycle 对象。API 26以后，SupportActivity、fragment 等组默认实现了该接口。
* `LifecycleObserver`接口：Lifecycle 的观察者，没有任何方法，主要依靠`@OnLifecycleEvent`起效果。

```java
public class MyObserver implements LifecycleObserver {
    @OnLifecycleEvent(Lifecycle.Event.ON_RESUME)
    public void connectListener() {
        ...
    }

    @OnLifecycleEvent(Lifecycle.Event.ON_PAUSE)
    public void disconnectListener() {
        ...
    }
}

myActivity.getLifecycle().addObserver(new MyObserver());
```

`MyObserver`组件的方法会随着 myActivity 的各种生命而得到调用了。**Lifecycle 是 LiveData 和 ViewModel 的基础。**



#### LiveData

LiveData 简单来说就是一个可以根据观察者自身生命周期，在观察者需要结束时自动解绑的 Observable，并且结合了 DataBingding 的特点，LiveData 自身数据改变时可以通知所有的观察者对象。

LiveData 是 一个 abstract 类，有3个关键方法：

* `onActive`：LiveData 注册的观察者数量从 0 到 1时会执行，相当于初始化方法
* `onInactive`：LiveData 注册的观察者数量回到 0 时会执行
* `setValue`：数据改变通知所有观察者

```java
public class MyLiveData extends LiveData<MyData> {

    public MyLiveData(Context context) {
        // Initialize service
    }

    @Override
    protected void onActive() {
        // Start listening
    }

    @Override
    protected void onInactive() {
        // Stop listening
    }
}
```

LiveData 和观察者之间是一个双向绑定的过程，实际上，当观察者（`LifecycleOwner`）注册到 LiveData 的时候，LiveData 也会在内部初始化一个 `LifecycleObserver`去观察它的观察者。

```java
//LiveData的添加观察者的方法
public void observe(@NonNull LifecycleOwner owner, @NonNull Observer<T> observer) {
    if (owner.getLifecycle().getCurrentState() == DESTROYED) {
        // ignore
        return;
    }

    //LiveData会初始化一个LifecycleObserver去观察它的观察者
    LifecycleBoundObserver wrapper = new LifecycleBoundObserver(owner, observer);

    LifecycleBoundObserver existing = mObservers.putIfAbsent(observer, wrapper);

    if (existing != null && existing.owner != wrapper.owner) {
        throw new IllegalArgumentException("Cannot add the same observer"
                + " with different lifecycles");
    }
    if (existing != null) {
        return;
    }
    owner.getLifecycle().addObserver(wrapper);
}
```



#### ViewModel

ViewModel 是用来存储和管理 UI 相关的数据，这样在配置发生变化（例如：屏幕旋转）时，数据就不会丢失。注意在 ViewModel 内部不应该持有外部 View 的引用，它的生命周期比  Activity/Fragment 都长，引用就会造成内存泄露。

ViewModel 之所以能在 Activity/Fragment 重建的时候依旧能保持，主要是通过`ViewModelProviders`创建ViewModel，而不是 new 一个 ViewModel。

```java
// 获取ViewModel，绑定当前的activity的生命周期
mModel = ViewModelProviders.of(this).get(MyViewModel.class);
```

`ViewModelProviders`通过`ViewModelStore`来管理 ViewModel，`ViewModelStore`的一个 map 容器存储 ViewModel，通过 Activity 作为 key 区分，假设是同一个 Activity (哪怕不是同一个对象)，就返回同一个 ViewModel，直到 Activity 销毁则移除。



**ViewModel 使用场景**

* 用来保存 UI 的数据，比传统方式会有一些优势。
* 在同一个 actitivity 的多个 Fragment 之间共享数据。



**ViewModel vs SavedInstanceState**

* ViewModels 提供了一种在配置更改时保存数据的简便方式，但是如果应用进程被操作系统杀死，那么数据则没有机会被恢复。
* 通过 SavedInstanceState 保存的数据，存在于操作系统进程的内存中。当用户离开应用数个小时之后，应用的进程很有可能被操作系统杀死，通过 SavedInstanceState 保存的数据，则可以在 Activity 或者 Fragment 重新创建的时候，在其中的 onCreate() 方法中通过 Bundle 恢复数据。



### MVVM 优势 

1. 数据驱动

   支持 MVVM 的人都会养成一个概念，View 是由给与它的数据决定的，View 的变化也应该是数据的变化引起的。

2. 断开引用

   ViewModel 不需要关心 View 是怎么样的，不需要调用 View 的方法，因此也不需要再持有 View 接口的引用，这种架构更方便重构、也不需要再从 Presenter 抽出一个个 Logic，可以直接针对 ViewModel 写单元测试。

3. ViewModel 重用性更好

   ViewModel 相当于一个高内聚的数据获取器，不再局限于于被哪个 View 使用，因此它的可用性更好，界面 A 可以用，界面 B 也可以用。

4. 更少的代码

   MVVM 一般会由框架层实现数据和 View 的双向绑定，因此代码会更加精简。
