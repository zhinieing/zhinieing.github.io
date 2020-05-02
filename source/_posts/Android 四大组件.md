---
title: Android 四大组件
date: 2017-10-12 15:40:38
categories:
- 源码分析
tags:
- Android
- source code
---
> Android 系统对四大组件的过程进行了很大程度的封装，本文侧重于对四大组件工作过程的分析，通过分析他们的工作过程理解系统内部运行机制，加深我们对 Android 整体系统结构的认识。

<!--more-->

**Tips：**

1. 除了`BroadcastReceiver`，其他三种组件都必须`AndroidManifest`中注册
2. 除了`ContentProvider`，其他三种组件需要借助`Intent`


## Activity 启动过程

* `startActivity`方法有好几种重载方式，但最终都会调用`startActivityForResult`方法，在其中调用了`Instrumentation`的`execStartActivity`方法。
* 在`Instrumentation`的`execStartActivity`方法中先通过`ActivityManagerNative.getDefault`得到 AMS 对象，调用其`startActivity`方法，最后执行`checkStartActivityResult`来检查启动 Activity 的结果。
* `ActivityManagerService`调用`ActivityStarter.startActivityMayWait`。经过一系列复杂的调用，收集并记录 Activity 的启动信息，调整 ActivityStack（让栈顶的 Activity 进入 pause 状态）。
* 最后在`ActivityStackSupervisor`的`realStartActivityLocked`方法调用`app.thread.scheduleLaunchActivity`方法。也就是说，`ActivityManagerService`调用`ApplicationThread`的`scheduleLaunchActivity`接口方法，在其中通过 Handler 发送了一个`LAUNCH_ACTIVITY`的消息。
* 在 Handler 的`handlerMessage`方法中调用了`ActivityThread`的`handlerLaunchActivity`方法，在其中又执行了`performLaunchActivity`方法。
* `performLaunchActivity`方法主要完成了如下几件事：
  1. 从`ActivityClientRecord`中获取带启动的 Activit 的组件信息
  2. 通过`Instrumentation`的`newActivity`方法使用类加载器创建 Activity 对象
  3. 通过`LoadedApk`的`makeApplication`方法来尝试创建 Application 对象
  4. 创建`ContextImpl`对象并通过 Activity 的 attach 方法来完成一些重要数据的初始化
  5. 调用 Activity 的 onCreate 方法
* 最终执行 ActivityThread 的`handlerResumeActivity`方法，然后调用 Activity 的 onResume 方法和 makeVisible 方法，把 decorView 添加到 WindowManage。



## Service 启动过程

* Service 的启动过程从`ContextWrapper`的`startService`开始，调用了`ContextImpl`的`startService`，在其中执行了`startServiceCommon`方法。
* `startServiceCommon`方法中先通过`ActivityManagerNative.getDefault`得到 AMS 对象，调用其`startService`方法，经过一系列复杂的调用，最后在`realStartServiceLocked`方法调用`app.thread.scheduleCreateService`方法。也就是说，`ActivityManagerService`调用`ApplicationThread`的`scheduleCreateService`接口方法，在其中通过 Handler 发送了一个`CREATE_SERVICE`的消息。
* 在 Handler 的`handlerMessage`方法中调用了`ActivityThread`的`handlerCreateService`方法。
  1. 首先通过类加载器创建 Service 对象
  2. 尝试创建 Application 对象
  3. 创建`ContextImpl`对象并通过 Service 的 attach 方法来完成一些重要数据的初始化
  4. 调用 Service 的 onCreate 方法
* 最终执行 ActivityThread 的`handlerServiceArgs`方法调用 Service 的`onStartCommand`方法。



## Service 绑定过程

- Service 的绑定过程从`ContextWrapper`的`bindService`开始，调用了`ContextImpl`的`bindService`，在其中执行了`bindServiceCommon`方法。
- `bindServiceCommon`方法中先通过`ActivityManagerNative.getDefault`得到 AMS 对象，调用其`bindService`方法，经过一系列复杂的调用，最后在`realStartServiceLocked`方法调用`app.thread.scheduleBindService`方法。也就是说，`ActivityManagerService`调用`ApplicationThread`的`scheduleBindService`接口方法，在其中通过 Handler 发送了一个`BIND_SERVICE`的消息。
- 在 Handler 的`handlerMessage`方法中调用了`ActivityThread`的`handlerBindService`方法。
  1. 首先 Service 的 token 取出 Service 对象
  2. 调用 Service 的 onBind 方法
  3. 调用 AMS 的`publishService`通知客户端成功连接 Service



## BroadcastReceiver 工作过程

**广播的注册过程**

**静态注册**：在`AndroidManifest`中注册，是由 PMS 来完成整个注册过程的。
**动态注册**：从`ContextWrapper`的`registerReceiver`开始，调用了`ContextImpl`的`registerReceiver`，在其中执行了`registerReceiverInternal`方法。通过`ActivityManagerNative.getDefault`得到 AMS 对象，调用其`registerReceiver`方法来完成注册。

**广播的发送和接受过程**

* 从`ContextWrapper`的`sendBroadcast`开始，调用了`ContextImpl`的`sendBroadcast`方法，通过`ActivityManagerNative.getDefault`得到 AMS 对象，调用其`broadcastIntent`方法。
* AMS 会根据 intent-filter 查找出匹配的广播接收者添加到`BroadcastQuene`中，最后调用了`ApplicationThread`的`scheduleRegisteredReceiver`接口方法，他通过`InnerReceiver`来实现广播的接收。
* `InnerReceiver`最终会执行 BroadcastReceiver 的 onReceive 方法。



## ContentProvider 工作过程

ContentProvider 的 onCreate 要优先于 Application 的 onCreate 而执行。

* 当一个应用启动或是 ContentProvider 所在的进程被 AMS 启动后，其入口方法为`ActivityThread`的 main 方法，它是一个静态方法，首先会创建`ActivityThread`的实例，然后执行其 attach 方法将`ApplicationThread`对象通过 AMS 的`attachApplication`方法跨进程传递给 AMS。
* AMS 的`attachApplication`方法调用了`attachApplicationLocked`方法，`attachApplicationLocked`方法中又调用了`ApplicationThread`的`bindApplication`，在其中通过 Handler 发送了一个`BIND_APPLICATION`的消息。
* 在 Handler 的`handlerMessage`方法中调用了`ActivityThread`的`handlerBindApplication`方法。
  1. 创建 ContextImpl 和 Instrumentation
  2. 创建 Application 对象
  3. 启动当前进程的 ContentProvider 并调用其 onCreate 方法
  4. 调用 Application 的 onCreate 方法
