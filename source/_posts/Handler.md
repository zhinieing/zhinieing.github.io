---
title: Handler
date: 2017-11-06 13:20:17
categories:
- 源码分析
tags:
- Android
- source code
---
> Handler 是 Android 消息机制的上层接口，用来解决线程之间的通信。接下来将介绍一下 Handler 的运行机制、Handler 所附带的 MessageQueue 和 Looper 的工作过程。

<!--more-->

## Handler 工作流程浅析

> 异步通信准备 => 消息入队 => 消息循环 => 消息处理


1. 异步通信准备
   假定是在主线程创建`Handler`，则会直接在主线程中创建处理器对象 `Looper`、消息队列对象 `MessageQueue` 和 Handler 对象。需要注意的是，`Looper` 和 `MessageQueue` 均是属于其 **创建线程** 的。`Looper` 对象的创建一般通过 `Looper.prepareMainLooper()` 和 `Looper.prepare()` 两个方法，而创建 `Looper` 对象的同时，将会自动创建 `MessageQueue`，创建好 `MessageQueue` 后，`Looper` 将自动进入消息循环。此时，`Handler` 自动绑定了主线程的 `Looper` 和 `MessageQueue`。
2. 消息入队
   工作线程通过 `Handler` 发送消息 `Message` 到消息队列 `MessageQueue` 中，消息内容一般是 UI 操作。发送消息一般都是通过 `Handler.sendMessage(Message msg)` 和 `Handler.post(Runnabe r)` 两个方法来进行的。而入队一般是通过 `MessageQueue.enqueueeMessage(Message msg,long when)` 来处理。
3. 消息循环
   主要分为「消息出队」和「消息分发」两个步骤，`Looper` 会通过循环 **取出** 消息队列 `MessageQueue` 里面的消息 `Message`，并 **分发** 到创建该消息的处理者 `Handler`。如果消息循环过程中，消息队列 `MessageQueue` 为空队列的话，则线程阻塞。
4. 消息处理 `Handler` 接收到 `Looper` 发来的消息，开始进行处理。





## 对于 Handler ，一些需要注意的地方

- 1 个线程 `Thread` 只能绑定 1个循环器 `Looper`，但可以有多个处理者 `Handler`
- 1 个循环器 `Looper` 可绑定多个处理者 `Handler`
- 1 个处理者 `Handler` 只能绑定 1 个 1 个循环器 `Looper`





## 消息机制具体流程分析

* `Handler`通过`sendMessage`或者`post`发送消息，最后都会调用`sendMessageAtTime`将`Message`交给`MessageQueue`
* `MessageQueue`调用其`enqueueMessage`方法将`Message`以链表的形式放入队列中
* `Looper`的`loop`方法循环调用`MessageQueue.next()`取出消息，通过`msg.target`获取目标`Handler`，并且调用`Handler`的`dispatchMessage`来处理消息
* 在`dispatchMessage`中，分别判断`msg.callback`也就是post方法、`mCallback`也就是构造方法传入的`Callback`不为空就执行他们的回调，如果都为空就执行我们最常用重写的`handleMessage`。





## 最后谈谈 Handler 的内存泄露问题

当使用内部类（包括匿名类）来创建`Handler`的时候，`Handler`对象会隐式地持有 Activity 的引用，即可能会造成内存泄漏。

解决方法：静态内部类 + 弱引用。

```Java
static class MyHandler extends Handler {
    WeakReference<Activity > mActivityReference;
    MyHandler(Activity activity) {
        mActivityReference= new WeakReference<Activity>(activity);
    }
    @Override
    public void handleMessage(Message msg) {
        final Activity activity = mActivityReference.get();
        if (activity != null) {
            mImageView.setImageBitmap(mBitmap);
        }
    }
}
```



## 关于 HandlerThread 和 IntentService

**`HandlerThread`**是一种可以使用`Handler`的 Thread。普通的 Thread 主要用于在 run 方法中执行一个耗时任务，而`HandlerThread`在内部创建了消息队列，外界需要通过`Handler`的消息方式来通知其执行一个具体的任务。



**`IntentService`**封装了`HandlerThread`和`Handler`。

工作流程如下：

1. 在`onCreate`方法中创建了一个`HandlerThread`，然后使用它的`Looper`来构造一个`Handler`对象`mServiceHandler`。
2. 在`onStartCommand`中调用了`onStart`，在`onStart`中把传进来的`Intent`通过`mServiceHandler`的`sendMessage`方法发送出去。
3. `mServiceHandler`在其`handleMessage`方法中先调用`onHandlerIntent`，执行完任务后调用`stopSelf`终止服务。

