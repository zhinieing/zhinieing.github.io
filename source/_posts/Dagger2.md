---
title: Dagger2
date: 2018-03-06 14:00:43
categories:
- 开源库
tags:
- Android
- library
---
> Dagger2 是 Dagger 的升级版，是一个依赖注入框架。Dagger2 与其他依赖注入框架不同，它是通过 apt 插件在编译阶段生成相应的注入代码。依赖注入是面向对象编程的一种设计模式，其目的是为了降低程序耦合，这个耦合就是类之间的依赖引起的。

<!--more-->

## MVP

在 mvp 中，最常见的一种依赖关系，就是 Activity 持有 presenter 的引用，并在 Activity 中实例化这个 presenter，即 Activity 依赖 presenter，presenter 又需要依赖 View 接口，从而更新 UI。


```java
public class MainActivity extends AppCompatActivity implements IView {
    private MainPresenter mainPresenter;
    ...
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        //实例化presenter 将view传递给presenter
        mainPresenter = new MainPresenter(this);
        //调用Presenter方法加载数据
         mainPresenter.loadData();
         
         ...
    }
    
    @Override
	public void onClearText() {
        ...
	}
}

public class MainPresenter {
    private IView mView;
    
    MainPresenter(IView view) {
        mView = view;
    }
    
    public void loadData() {
        //调用model层方法，加载数据
        ...
        //回调方法成功时
        mView.updateUI();
    }
}

public interface ILoginView {
	public void onClearText();
}
```





## Dagger2 依赖注入的 MVP

```java
public class MainActivity extends AppCompatActivity implements IView {
    @Inject
    MainPresenter mainPresenter;
    ...
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
         
         DaggerMainComponent.builder()
                .mainModule(new MainModule(this))
                .build()
                .inject(this);
        //调用Presenter方法加载数据
         mainPresenter.loadData();
         
         ...
    }

    @Override
	public void onClearText() {
        ...
	}
}

public class MainPresenter {
    private IView;
    
    @Inject
    MainPresenter(IView view) {
        mView = view;
    }    
    public void loadData() {
        //调用model层方法，加载数据
        ...
        //回调方法成功时
        mView.updateUI();
    }
}

public interface ILoginView {
	public void onClearText();
}

@Module
public class MainModule {
    private final IView mView;

    public MainModule(IView view) {
        mView = view;
    }

    @Provides
    MainView provideMainView() {
        return mView;
    }
}

@Component(modules = MainModule.class)
public interface MainComponent {
    void inject(MainActivity activity);
}

```

* `@Inject`带有此注解的属性或构造方法将参与到依赖注入中，Dagger2 会实例化有此注解的类
* `@Module`带有此注解的类，用来提供依赖，里面定义一些用`@Provides`注解的以`provide`开头的方法，这些方法就是所提供的依赖，Dagger2 会在该类中寻找实例化某个类所需要的依赖。
* `@Component`用来将`@Inject`和`@Module`联系起来的桥梁，从`@Module`中获取依赖并将依赖注入给`@Inject`。



### Dagger2 注入原理

先了解类图及辅助类的生成规则：

![mage-20180331000001](../Dagger2/image-201804031417535.png)

* 带`@Component`注解 ：生成 `Dagger_`(带`@Component`注解接口名称)。
* 带`@Module`注解 ：生成 (带`@Mudule`类名)_(带`@Provides`注解的方法名)`Factory`。
* 带`@Inject`注解：生成 (需要注入对象所在的类名)`_MembersInjector`。


下面是 Dagger2 生成的注入代码，我们先看 MainPresenter 所对应的注入类。

```java
public class MainPresenter {
    IView mView;
    @Inject
    MainPresenter(IView view) {
        mView = view;
    }
 }


public final class MainPresenter_Factory implements Factory<MainPresenter> {
  private final Provider<IView> viewProvider;

  public MainPresenter_Factory(Provider<IView> viewProvider) {
    assert viewProvider != null;
    this.viewProvider = viewProvider;
  }

  @Override
  public MainPresenter get() {
    return new MainPresenter(viewProvider.get());
  }

  public static Factory<MainPresenter> create(Provider<IView> viewProvider) {
    return new MainPresenter_Factory(viewProvider);
  }
}
```



MainModule 所对应的注入类。

```java
@Module
public class MainModule {
    private final IView mView;

    public MainModule(IView view) {
        mView = view;
    }

    @Provides
    IView provideMainView() {
        return mView;
   }   
}


public final class MainModule_ProvideMainViewFactory implements Factory<IView> {
  private final MainModule module;

  public MainModule_ProvideMainViewFactory(MainModule module) {
    assert module != null;
    this.module = module;
  }

  @Override
  public IView get() {
    return Preconditions.checkNotNull(
        module.provideMainView(), "Cannot return null from a non-@Nullable @Provides method");
  }

  public static Factory<IView> create(MainModule module) {
    return new MainModule_ProvideMainViewFactory(module);
  }
}
```

看到这里我们应该明白了 MainPresenter 的实例化过程。MainPresenter 会对应的有一个工厂类，在这个类的`get()`方法中进行 MainPresenter 创建，而 MainPresenter 所需要的 View 依赖，是由 MainModule 里定义的以`provide`开头的方法所对应的工厂类提供的。

MainPresenter 实例和`@Inject`注解的 MainPresenter 关联是在 Component 里实现的。

```java
@Component(modules = MainModule.class)
public interface MainComponent {
    void inject(MainActivity activity);
}

public final class DaggerMainComponent implements MainComponent {
  private Provider<IView> provideMainViewProvider;

  private Provider<MainPresenter> mainPresenterProvider;

  private MembersInjector<MainActivity> mainActivityMembersInjector;

  private DaggerMainComponent(Builder builder) {
    assert builder != null;
    initialize(builder);
  }

  public static Builder builder() {
    return new Builder();
  }

  @SuppressWarnings("unchecked")
  private void initialize(final Builder builder) {

    this.provideMainViewProvider = MainModule_ProvideMainViewFactory.create(builder.mainModule);

    this.mainPresenterProvider = MainPresenter_Factory.create(provideMainViewProvider);

    this.mainActivityMembersInjector = MainActivity_MembersInjector.create(mainPresenterProvider);
  }

  @Override
  public void inject(MainActivity activity) {
    mainActivityMembersInjector.injectMembers(activity);
  }

  public static final class Builder {
    private MainModule mainModule;

    private Builder() {}

    public MainComponent build() {
      if (mainModule == null) {
        throw new IllegalStateException(MainModule.class.getCanonicalName() + " must be set");
      }
      return new DaggerMainComponent(this);
    }

    public Builder mainModule(MainModule mainModule) {
      this.mainModule = Preconditions.checkNotNull(mainModule);
      return this;
    }
  }
}
```

在 MainComponent 里定义的`Inject`方法的实现里调用了`mainActivityMembersInjector.injectMembers(activity)`方法，将我们的 MainActivity 注入到该类中。

`MainActivity_MembersInjector`所对应的注入类。

```java
public final class MainActivity_MembersInjector implements MembersInjector<MainActivity> {
  private final Provider<MainPresenter> mainPresenterProvider;

  public MainActivity_MembersInjector(Provider<MainPresenter> mainPresenterProvider) {
    assert mainPresenterProvider != null;
    this.mainPresenterProvider = mainPresenterProvider;
  }

  public static MembersInjector<MainActivity> create(
      Provider<MainPresenter> mainPresenterProvider) {
    return new MainActivity_MembersInjector(mainPresenterProvider);
  }

  @Override
  public void injectMembers(MainActivity instance) {
    if (instance == null) {
      throw new NullPointerException("Cannot inject members into a null reference");
    }
    instance.mainPresenter = mainPresenterProvider.get();
  }

  public static void injectMainPresenter(
      MainActivity instance, Provider<MainPresenter> mainPresenterProvider) {
    instance.mainPresenter = mainPresenterProvider.get();
  }
}
```

最后将`mainPresenterProvider`中创建好的 MainPresenter 实例赋值给`instance(MainActivity)`的成员 mainPresenter，这样我们用`@Inject`标注的 mainPresenter 就得到了实例化，接着就可以在代码中使用了。
