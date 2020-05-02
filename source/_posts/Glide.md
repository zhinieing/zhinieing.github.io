---
title: Glide
date: 2017-11-30 13:24:21
categories:
- 开源库
tags:
- Android
- library
---
> Glide 是 Google 推荐的一套快速高效的图片加载框架，功能强大且使用方便。它在使用上大致分为 with、load、into 三个步骤，接下来将分别围绕这三个方法来解析。

<!--more-->

## with 方法

根据传入的 context 分为

1. Application 对象，和应用程序的生命周期同步
2. 非 Application 对象，使用隐藏 Fragment（`RequestManagerFragment`）得到生命周期

with 方法返回了一个`RequestManager`对象。


## load 方法

返回默认`DrawableTypeRequest`对象。指定`asBitmap、asGif`时分别返回`BitmapTypeRequest`对象、`GifTypeRequest`对象。



## into 方法

`RequsetBuilder`的`into`方法中创建了`buildRequest`，创建请求，调用了`Engine`的`oad`方法，最后设置`target`。

### Engine

> 任务创建，发起，回调，管理存活和缓存的资源

### load()

```java
public  LoadStatus load(
    GlideContext glideContext,
    Object model,
    Key signature,
    int width,
    int height,
    Class resourceClass,
    Class transcodeClass,
    Priority priority,
    DiskCacheStrategy diskCacheStrategy,
    Map, Transformation> transformations,
    boolean isTransformationRequired,
    Options options,
    boolean isMemoryCacheable,
    boolean useUnlimitedSourceExecutorPool,
    ResourceCallback cb) {
  Util.assertMainThread();
  long startTime = LogTime.getLogTime();
  //创建key，这是给每次加载资源的唯一标示。
  EngineKey key = keyFactory.buildKey(model, signature, width, height, transformations,
      resourceClass, transcodeClass, options);
  //从内存缓存中获取资源，获取成功后会放入到activeResources中
  EngineResource cached = loadFromCache(key, isMemoryCacheable);
  if (cached != null) {
    //如果有，那么直接利用当前缓存的资源。
    cb.onResourceReady(cached, DataSource.MEMORY_CACHE);
    if (Log.isLoggable(TAG, Log.VERBOSE)) {
      logWithTimeAndKey("Loaded resource from cache", startTime, key);
    }
    return null;
  }
  //这是一个二级内存的缓存引用，很简单用了一个Map>>装载起来的。
  //从存活的资源中加载资源，资源加载完成后，再将这个缓存数据放到一个 value 为软引用的 activeResources map 中，并计数引用数，在图片加载完成后进行判断，如果引用计数为空则回收掉。
  EngineResource active = loadFromActiveResources(key, isMemoryCacheable);
  if (active != null) {
    cb.onResourceReady(active, DataSource.MEMORY_CACHE);
    if (Log.isLoggable(TAG, Log.VERBOSE)) {
      logWithTimeAndKey("Loaded resource from active resources", startTime, key);
    }
    return null;
  }
  //根据key获取缓存的job。
  EngineJob current = jobs.get(key);
  if (current != null) {
    current.addCallback(cb);
    if (Log.isLoggable(TAG, Log.VERBOSE)) {
      logWithTimeAndKey("Added to existing load", startTime, key);
    }
    return new LoadStatus(cb, current);
  }
  //创建job
  EngineJob engineJob = engineJobFactory.build(key, isMemoryCacheable,
      useUnlimitedSourceExecutorPool);
  DecodeJob decodeJob = decodeJobFactory.build(
      glideContext,
      model,
      key,
      signature,
      width,
      height,
      resourceClass,
      transcodeClass,
      priority,
      diskCacheStrategy,
      transformations,
      isTransformationRequired,
      options,
      engineJob);
  jobs.put(key, engineJob);
  engineJob.addCallback(cb);
  //放入线程池，执行
  engineJob.start(decodeJob);
  if (Log.isLoggable(TAG, Log.VERBOSE)) {
    logWithTimeAndKey("Started new load", startTime, key);
  }
  return new LoadStatus(cb, engineJob);
}
```



### load 调用处理流程图

> `DecodeJob`是整个任务的核心部分。使用了`LruCache`、弱引用二级内存缓存和`DiskLruCache`磁盘缓存。

![mage-20180402000420](../Glide/image-201804020004200.png)



### EngineJob

>调度`DecodeJob`，添加，移除资源回调，并 notify 回调。



### start(DecodeJob decodeJob)

> 通过线程池调度一个`DecodeJob`任务。



### MainThreadCallback

> 实现了`Handler.Callback`接口，用于`Engine`任务完成时回调主线程。



### DecodeJob

> 实现了`Runnable`接口，调度任务的核心类，整个请求的繁重工作都在这里完成：处理来自缓存或者原始的资源，应用转换动画以及`transcode`。负责根据缓存类型获取不同的`Generator`加载数据，数据加载成功后回调`DecodeJob`的`onDataFetcherReady`方法对资源进行处理。

![mage-20180402000916](../Glide/image-201804020009168.png)