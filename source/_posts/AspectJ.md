---
title: AspectJ
date: 2018-03-27 14:33:19
categories:
- 程序设计
tags:
- Android
- AOP
- AspectJ
---
> 如果说，OOP 如果是把问题划分到单个模块的话，那么 AOP 就是把涉及到众多模块的某一类问题进行统一管理。这里通过几个小例子，讲解在 Android 开发中，如何运用 AOP 的方式，进行全局切片管理，达到简洁优雅，一劳永逸的效果。

<!--more-->

## SingleClickAspect，防止 View 被连续点击出发多次事件

给点击事件加一个切入点，添加一个注解

```Java
@Retention(RetentionPolicy.CLASS)
@Target(ElementType.METHOD)
public @interface SingleClick {
}
```

然后编写我们的 Aspect 类

```java
@Aspect
public class SingleClickAspect {

    public static final String TAG="SingleClickAspect";
    public static final int MIN_CLICK_DELAY_TIME = 600;
    static int TIME_TAG = R.id.click_time;

    @Pointcut("execution(@com.ditclear.app.aop.annotation.SingleClick * *(..))")//方法切入点
    public void methodAnnotated(){

    }

    @Around("methodAnnotated()")//在连接点进行方法替换
    public void aroundJoinPoint(ProceedingJoinPoint joinPoint) throws Throwable{
        View view=null;
        for (Object arg: joinPoint.getArgs()) {
            if (arg instanceof View) view= ((View) arg);
        }
        if (view!=null){
            Object tag=view.getTag(TIME_TAG);
            long lastClickTime= (tag!=null)? (long) tag :0;
            if (BuildConfig.DEBUG) {
                Log.d(TAG, "lastClickTime:" + lastClickTime);
            }
            long currentTime = Calendar.getInstance().getTimeInMillis();
            if (currentTime - lastClickTime > MIN_CLICK_DELAY_TIME) {//过滤掉600毫秒内的连续点击
                view.setTag(TIME_TAG, currentTime);
                if (BuildConfig.DEBUG) {
                    Log.d(TAG, "currentTime:" + currentTime);
                }
                joinPoint.proceed();//执行原方法
            }
        }
    }
}
```

接下来是使用

```Java
@SingleClick
public void onClick(View view) {
}
```



## CheckLoginAspect 拦截未登录用户的权限

```Java
@Aspect
public class CheckLoginAspect {

    @Pointcut("execution(@com.app.annotation.aspect.CheckLogin * *(..))")//方法切入点
    public void methodAnnotated() {
    }

    @Around("methodAnnotated()")//在连接点进行方法替换
    public void aroundJoinPoint(ProceedingJoinPoint joinPoint) throws Throwable {
        if (null == SpUtil.getUser()) {
            Snackbar.make(App.getAppContext().getCurActivity().getWindow().getDecorView(), "请先登录!", Snackbar.LENGTH_LONG)
                    .setAction("登录", new View.OnClickListener() {
                        @Override
                        public void onClick(View view) {
                            TRouter.go(C.LOGIN);
                        }
                    }).show();
            return;
        }
        joinPoint.proceed();//执行原方法
    }
}
```

使用方法:

```java
public class AdvisePresenter extends AdviseContract.Presenter {

    @CheckLogin
    public void createMessage(String msg) {
        _User user = SpUtil.getUser();
        ApiFactory.createMessage(
                new Message(ApiUtil.getPointer(
                        new _User(C.ADMIN_ID)), msg,
                        ApiUtil.getPointer(user),
                        user.objectId))
                .subscribe(
                        res -> mView.sendSuc(),
                        e -> mView.showMsg("消息发送失败!"));
    }

    @CheckLogin
    public void initAdapterPresenter(AdapterPresenter mAdapterPresenter) {
        mAdapterPresenter
                .setRepository(ApiFactory::getMessageList)
                .setParam(C.INCLUDE, C.CREATER)
                .setParam(C.UID, SpUtil.getUser().objectId)
                .fetch();
    }
}
```



## MemoryCacheAspect 内存缓存切片

```Java
@Aspect
public class MemoryCacheAspect {

    @Pointcut("execution(@com.app.annotation.aspect.MemoryCache * *(..))")//方法切入点
    public void methodAnnotated() {
    }

    @Around("methodAnnotated()")//在连接点进行方法替换
    public Object aroundJoinPoint(ProceedingJoinPoint joinPoint) throws Throwable {
        MethodSignature methodSignature = (MethodSignature) joinPoint.getSignature();
        String methodName = methodSignature.getName();
        MemoryCacheManager mMemoryCacheManager = MemoryCacheManager.getInstance();
        StringBuilder keyBuilder = new StringBuilder();
        keyBuilder.append(methodName);
        for (Object obj : joinPoint.getArgs()) {
            if (obj instanceof String) keyBuilder.append((String) obj);
            else if (obj instanceof Class) keyBuilder.append(((Class) obj).getSimpleName());
        }
        String key = keyBuilder.toString();
        Object result = mMemoryCacheManager.get(key);//key规则 ： 方法名＋参数1+参数2+...
        LogUtils.showLog("MemoryCache", "key：" + key + "--->" + (result != null ? "not null" : "null"));
        if (result != null) return result;//缓存已有，直接返回
        result = joinPoint.proceed();//执行原方法
        if (result instanceof List && result != null && ((List) result).size() > 0 //列表不为空
                || result instanceof String && !TextUtils.isEmpty((String) result)//字符不为空
                || result instanceof Object && result != null)//对象不为空
            mMemoryCacheManager.add(key, result);//存入缓存
        LogUtils.showLog("MemoryCache", "key：" + key + "--->" + "save");
        return result;
    }
}
```

看看 Apt 生成的 Factory：

```Java
public final class InstanceFactory {
  /**
   * @此方法由apt自动生成 */
  @MemoryCache
  public static Object create(Class mClass) throws IllegalAccessException, InstantiationException {
     switch (mClass.getSimpleName()) {
      case "AdvisePresenter": return  new AdvisePresenter();
      case "ArticlePresenter": return  new ArticlePresenter();
      case "HomePresenter": return  new HomePresenter();
      case "LoginPresenter": return  new LoginPresenter();
      case "UserPresenter": return  new UserPresenter();
      default: return mClass.newInstance();
    }
  }
}
```



## TimeLogAspect 自动打印方法的耗时

```Java
@Aspect
public class TimeLogAspect {

    @Pointcut("execution(@com.app.annotation.aspect.TimeLog * *(..))")//方法切入点
    public void methodAnnotated() {
    }

    @Pointcut("execution(@com.app.annotation.aspect.TimeLog *.new(..))")//构造器切入点
    public void constructorAnnotated() {
    }

    @Around("methodAnnotated() || constructorAnnotated()")//在连接点进行方法替换
    public Object aroundJoinPoint(ProceedingJoinPoint joinPoint) throws Throwable {
        MethodSignature methodSignature = (MethodSignature) joinPoint.getSignature();
        LogUtils.showLog("TimeLog getDeclaringClass", methodSignature.getMethod().getDeclaringClass().getCanonicalName());
        String className = methodSignature.getDeclaringType().getSimpleName();
        String methodName = methodSignature.getName();
        long startTime = System.nanoTime();
        Object result = joinPoint.proceed();//执行原方法
        StringBuilder keyBuilder = new StringBuilder();
        keyBuilder.append(methodName + ":");
        for (Object obj : joinPoint.getArgs()) {
            if (obj instanceof String) keyBuilder.append((String) obj);
            else if (obj instanceof Class) keyBuilder.append(((Class) obj).getSimpleName());
        }
        String key = keyBuilder.toString();
        LogUtils.showLog("TimeLog", (className + "." + key + joinPoint.getArgs().toString() + " --->:" + "[" + (TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startTime)) + "ms]"));// 打印时间差
        return result;
    }
}
```

使用方法：

```Java
@TimeLog
public void onCreate() {
    super.onCreate();
    mApp = this;
    SpUtil.init(this);
    store = new Stack<>();
    registerActivityLifecycleCallbacks(new SwitchBackgroundCallbacks());
}
```



## SysPermissionAspect 运行时权限申请

```Java
@Aspect
public class SysPermissionAspect {

    @Around("execution(@com.app.annotation.aspect.Permission * *(..)) && @annotation(permission)")
    public void aroundJoinPoint(ProceedingJoinPoint joinPoint, Permission permission) throws Throwable {
        AppCompatActivity ac = (AppCompatActivity) App.getAppContext().getCurActivity();
        new AlertDialog.Builder(ac)
                .setTitle("提示")
                .setMessage("为了应用可以正常使用，请您点击确认申请权限。")
                .setNegativeButton("取消", null)
                .setPositiveButton("允许", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        MPermissionUtils.requestPermissionsResult(ac, 1, permission.value()
                                , new MPermissionUtils.OnPermissionListener() {
                                    @Override
                                    public void onPermissionGranted() {
                                        try {
                                            joinPoint.proceed();//获得权限，执行原方法
                                        } catch (Throwable e) {
                                            e.printStackTrace();
                                        }
                                    }

                                    @Override
                                    public void onPermissionDenied() {
                                        MPermissionUtils.showTipsDialog(ac);
                                    }
                                });
                    }
                })
                .create()
                .show();
    }
}
```

使用方法：

```Java
@Permission(Manifest.permission.CAMERA)
public void takePhoto() {
    startActivityForResult(
            new Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                    .putExtra(MediaStore.EXTRA_OUTPUT,
                            Uri.fromFile(new File(getExternalCacheDir()+ "user_photo.png"))),
            C.IMAGE_REQUEST_CODE);
}
```