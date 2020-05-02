---
title: OkHttp
date: 2017-12-08 13:34:07
categories:
- 开源库
tags:
- Android
- library
---

> OkHttp 是一个高效的 HTTP 库:
* 支持 SPDY ，共享同一个 Socke t来处理同一个服务器的所有请求
* 如果 SPDY 不可用，则通过连接池来减少请求延时
* 无缝的支持 GZIP 来减少数据流量
* 缓存响应数据来减少重复的网络请求

<!--more-->

## 总体设计

![mage-20180402001207](../OkHttp/image-201804020012074.png)



## 请求流程图

![mage-20180402001511](../OkHttp/image-201804020015112.png)

> `OkHttpClient`内部缓存有`Cache`和`InternalCache`。



* 先创建`OkHttpClient`的实例，然后通过`Request.Builder()`创建Request对象
* 通过`Diapatcher`不断从`RequestQueue`中取出请求（`Call`），同步请求通过`Call.execute()`直接返回当前的`Response`，而异步请求会把当前的请求`Call.enqueue()`添加（`AsyncCall`）到请求队列中，并通过回调（`Callback`） 的方式来获取最后结果。
* 同步请求和异步请求最后都会通过拦截器链发起请求，根据是否已缓存调用`Cache`或`Network`这两类数据获取接口之一，从内存缓存或是服务器取得请求的数据。


## 文件下载进度监听

我们在 Glide 中把 HTTP 通讯组件由 HttpUrlConnection 替换成 OkHttp。监听下载进度的功能要依靠 OkHttp 的拦截器机制。关于 Glide 的 OkHttp 模块的具体替换过程，这里不展开讲解。

在 Glide 的 OkHttp 实现模块中启用一个自定义拦截器`ProgressInterceptor`。

```java
public class MyGlideModule implements GlideModule { 
    @Override 
    public void applyOptions(Context context, GlideBuilder builder) { 
    } 

    @Override 
    public void registerComponents(Context context, Glide glide) { 
        OkHttpClient.Builder builder = new OkHttpClient.Builder(); 
        builder.addInterceptor(new ProgressInterceptor()); 
        OkHttpClient okHttpClient = builder.build(); 
        //glide.register(GlideUrl.class, InputStream.class, new OkHttpGlideUrlLoader.Factory(okHttpClient));
    } 
}
```



先新建一个`ProgressListener`接口，用于作为进度监听回调的工具。

```java
public interface ProgressListener {
    void onProgress(int progress);
}
```



接着看自定义拦截器`ProgressInterceptor`的实现，我们在`ProgressInterceptor`中加入注册下载监听和取消注册下载监听的方法。同时我们通过 Response 的`newBuilder()`方法来创建一个新的 Response 对象，并把它的 body 替换成自定义的`ProgressResponseBody`，最终将新的 Response 对象进行返回。

```java
public class ProgressInterceptor implements Interceptor { 

    static final Map<String, ProgressListener> LISTENER_MAP = new HashMap<>();

    public static void addListener(String url, ProgressListener listener) {
        LISTENER_MAP.put(url, listener); 
    } 

    public static void removeListener(String url) { 
        LISTENER_MAP.remove(url); 
    } 

    @Override 
    public Response intercept(Chain chain) throws IOException { 
        Request request = chain.request(); 
        Response response = chain.proceed(request); 
        String url = request.url().toString(); 
        ResponseBody body = response.body(); 
        Response newResponse = response.newBuilder().body(new ProgressResponseBody(url, body)).build();
        return newResponse; 
    } 

}
```



然后我们来看自定义的`ProgressResponseBody`类，它继承自 OkHttp 的`ResponseBody`。我们在这个类当中编写具体的监听下载进度的逻辑。

```java
public class ProgressResponseBody extends ResponseBody {

    private static final String TAG = "ProgressResponseBody";

    private BufferedSource bufferedSource;

    private ResponseBody responseBody;

    private ProgressListener listener;

    public ProgressResponseBody(String url, ResponseBody responseBody) {
        this.responseBody = responseBody;
        listener = ProgressInterceptor.LISTENER_MAP.get(url);
    }

    @Override
    public MediaType contentType() {
        return responseBody.contentType();
    }

    @Override
    public long contentLength() {
        return responseBody.contentLength();
    }

    @Override 
    public BufferedSource source() {
        if (bufferedSource == null) {
            bufferedSource = Okio.buffer(new ProgressSource(responseBody.source()));
        }
        return bufferedSource;
    }

    private class ProgressSource extends ForwardingSource {

        long totalBytesRead = 0;

        int currentProgress;

        ProgressSource(Source source) {
            super(source);
        }

        @Override 
        public long read(Buffer sink, long byteCount) throws IOException {
            long bytesRead = super.read(sink, byteCount);
            long fullLength = responseBody.contentLength();
            if (bytesRead == -1) {
                totalBytesRead = fullLength;
            } else {
                totalBytesRead += bytesRead;
            }
            int progress = (int) (100f * totalBytesRead / fullLength);
            Log.d(TAG, "download progress is " + progress);
            if (listener != null && progress != currentProgress) {
                listener.onProgress(progress);
            }
            if (listener != null && totalBytesRead == fullLength) {
                listener = null;
            }
            currentProgress = progress;
            return bytesRead;
        }
    }
}
```



最后在将下载进度显示到界面上。

```java
public void loadImage(View view) {
    ProgressInterceptor.addListener(url, new ProgressListener() {
        @Override
        public void onProgress(int progress) {
            progressDialog.setProgress(progress);
        }
    });
    Glide.with(this)
         .load(url)
         .diskCacheStrategy(DiskCacheStrategy.NONE)
         .override(Target.SIZE_ORIGINAL, Target.SIZE_ORIGINAL)
         .into(new GlideDrawableImageViewTarget(image) {
             @Override
             public void onLoadStarted(Drawable placeholder) {
                 super.onLoadStarted(placeholder);
                 progressDialog.show();
             }

             @Override 
             public void onResourceReady(GlideDrawable resource, GlideAnimation<? super GlideDrawable> animation) {
                 super.onResourceReady(resource, animation);
                 progressDialog.dismiss();
                 ProgressInterceptor.removeListener(url);
             }
         });
}
```



## 文件上传进度监听

关键点是自定义支持进度反馈的`FileProgressRequestBody`类，它继承自 OkHttp 的`RequestBody`。重写 write 方法按照自定义的`SEGMENT_SIZE`来写文件，从而监听进度。

```java
public class FileProgressRequestBody extends RequestBody {

    public interface ProgressListener {
        void transferred( long size );
    }

    public static final int SEGMENT_SIZE = 2*1024; // okio.Segment.SIZE

    protected File file;
    protected ProgressListener listener;
    protected String contentType;

    public FileProgressRequestBody(File file, String contentType, ProgressListener listener) {
        this.file = file;
        this.contentType = contentType;
        this.listener = listener;
    }

    protected FileProgressRequestBody() {}

    @Override
    public long contentLength() {
        return file.length();
    }

    @Override
    public MediaType contentType() {
        return MediaType.parse(contentType);
    }

    @Override
    public void writeTo(BufferedSink sink) throws IOException {
        Source source = null;
        try {
            source = Okio.source(file);
            long total = 0;
            long read;

            while ((read = source.read(sink.buffer(), SEGMENT_SIZE)) != -1) {
                total += read;
                sink.flush();
                this.listener.transferred(total);

            }
        } finally {
            Util.closeQuietly(source);
        }
    }
}
```

`FileProgressRequestBody`以 2KB 为单位上传，对外暴露回调`ProgressListener`来发布进度。接着构造 Request 对象。

```java
protected Request generateRequest(String url){
    
    // 构造上传请求，模拟表单提交文件
    String formData = String.format("form-data;name=file; filename=%s", FileUtil.pickFileNameFromPath(fileInfo.filePath) );
    FileProgressRequestBody filePart = new FileProgressRequestBody( new File(fileInfo.filePath) , "application/octet-stream" , this );
    MultipartBody requestBody = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addPart( Headers.of("Content-Disposition",formData), filePart )
            .build();

    // 创建Request对象
    Request request = new Request.Builder()
            .url(url)
            .post(requestBody)
            .build();

    return request;
}
```

传入文件路径，formData 是与服务端的 header 约定，此处约定：name 是文件名称。定义文件上传的执行方法`doUpload`。

```java
protected int doUpload(String url){
    try {
        OkHttpClient httpClient = OkHttpClientMgr.Instance().getOkHttpClient();
        call = httpClient.newCall( generateRequest(url) );
        Response response = call.execute();
        if (response.isSuccessful()) {
            sbFileUUID = new StringBuilder();
            return readResponse(response, sbFileUUID);
        } else( ... ) { // 重试
            return STATUS_RETRY;
        }
    } catch (IOException ioe) {
        LogUtil.e(LOG_TAG, "exception occurs while uploading file!",ioe);
    }
    return isCancelled() ? STATUS_CANCEL : STATUS_FAILED_EXIT;
}
```

`readResponse()`方法就是每次上传后读取服务端的结果：上传成功，可以让服务端返回文件的 uuid，从`response.body()`读取 uuid；上传失败，和服务端约定一个状态码，执行重试。



## 文件分块上传

分块上传和断点下载很像，就是将文件分为多份来传输，从而实现暂停和继续传输。区别是断点下载的进度保存在客户端，分块上传的进度保存在服务器，每次可以通过文件的 md5 请求服务器，来获取最新的上传偏移量。但是这样明显效率偏低，客户端可以把 offSet 保存在内存，每上传一块文件服务器返回下一次的 offSet。

Okhttp 已经支持表单形式的文件上传，剩下的关键就是构造分块文件的`RequestBody`，对本地文件分块，和服务端约定相关 header，保存 offset 实现分块上传。我们这里直接继承之前实现的进度监听`RequestBody`。

```java
public class MDProgressRequestBody extends FileProgressRequestBody {

    protected final byte[] content;
    public MDProgressRequestBody(byte[] content, String contentType , ProgressListener listener) {
        this.content = content;
        this.contentType = contentType;
        this. listener = listener;
    }

    @Override
    public long contentLength() {
        return content.length;
    }

    @Override
    public void writeTo(BufferedSink sink) throws IOException {
        int offset = 0 ;
        //计算分块数
        count = (int) ( content.length / SEGMENT_SIZE + (content.length % SEGMENT_SIZE != 0?1:0) );
        for( int i=0; i < count; i++ ) {
            int chunk = i != count -1  ? SEGMENT_SIZE : content.length - offset;
            sink.buffer().write(content, offset, chunk );//每次写入SEGMENT_SIZE 字节
            sink.buffer().flush();
            offset += chunk;
            listener.transferred( offset );
        }
    }
}
```

`MDProgressRequestBody`传入 Byte 数组，从而实现了对文件的分块上传。



把文件切割成 Byte 数组的方法。

```java
public static byte[] getBlock(long offset, File file, int blockSize) {

    byte[] result = new byte[blockSize];
    RandomAccessFile accessFile = null;

    try {
        accessFile = new RandomAccessFile(file, "r");
        accessFile.seek(offset);
        int readSize = accessFile.read(result);
        if (readSize == -1) {
            return null;
        } else if (readSize == blockSize) {
            return result;
        } else {
            byte[] tmpByte = new byte[readSize];
            System.arraycopy(result, 0, tmpByte, 0, readSize);
            return tmpByte;
        }

    } catch (IOException e) {
        e.printStackTrace();
    } finally {
        if (accessFile != null) {
            try {
                accessFile.close();
            } catch (IOException e1) {
            }
        }
    }
    return null;
}
```



构造 Request 对象。

```java
protected Request generateRequest(String url) {

    // 获取分块数据，按照每次10M的大小分块上传
    final int CHUNK_SIZE = 10 * 1024 * 1024;

    //切割文件为10M每份
    byte[] blockData = FileUtil.getBlock(offset, new File(fileInfo.filePath), CHUNK_SIZE);
    if (blockData == null) {
        throw new RuntimeException(String.format("upload file get blockData faild，filePath:%s , offest:%d", fileInfo.filePath, offset));
    }
    curBolckSize = blockData.length;
    // 分块上传，客户端和服务端约定，name字段传文件分块的始偏移量
    String formData = String.format("form-data;name=%s; filename=file", offset);
    RequestBody filePart = new MDProgressRequestBody(blockData, "application/octet-stream ", this);
    MultipartBody requestBody = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addPart(Headers.of("Content-Disposition", formData), filePart)
            .build();
    // 创建Request对象
    Request request = new Request.Builder()
            .url(url)
            .post(requestBody)
            .build();
    return request;
}
```



定义文件上传的执行方法`doUpload`。

```java
protected int doUpload(String url){
    try {
        OkHttpClient httpClient = OkHttpClientMgr.Instance().getOkHttpClient();
        call = httpClient.newCall( generateRequest(url) );
        Response response = call.execute();
        if (response.isSuccessful()) {
            sbFileUUID = new StringBuilder();
            return readResponse(response,sbFileUUID);
        } else( ... ) { // 重试
            return STATUS_RETRY;
        }
    } catch (IOException ioe) {
        LogUtil.e(LOG_TAG, "exception occurs while uploading file!",ioe);
    }
    return isCancelled() ? STATUS_CANCEL : STATUS_FAILED_EXIT;
}
```



这里的`readRespones`读取服务端结果，更新offSet数值。

```java
protected int readResponse(Response response, StringBuilder sbFileUUID) {

    int exitStatus = STATUS_FAILED_EXIT;
    ResponseBody body = response.body();

    if (body == null) {
        LogUtil.e(LOG_TAG, "readResponse body is null!", new Throwable());
        return exitStatus;
    }

    try {
        String content = body.string();
        JSONObject jsonObject = new JSONObject(content);
        if (jsonObject.has("uuid")) { // 上传成功，返回UUID
            String uuid = jsonObject.getString("uuid");
            if (uuid != null && !uuid.isEmpty()) {
                sbFileUUID.append(uuid);
                exitStatus = STATUS_SUCCESS;
            } else {
                LogUtil.e(LOG_TAG, "readResponse fileUUID return empty! ");
            }
        } else if (jsonObject.has("offset")) { // 分块上传完成，返回新的偏移量
            long newOffset = (long) jsonObject.getLong("offset");
            if (newOffset != offset + curBolckSize) {
                LogUtil.e(LOG_TAG, "readResponse offest-value exception ! ");
            } else {
                offset = newOffset; // 分块数据上传完成，修正偏移
                exitStatus = STATUS_RETRY;
            }
        } else {
            LogUtil.e(LOG_TAG, "readResponse unexpect data , no offest、uuid field !");
        }
    } catch (Exception ex) {
        LogUtil.e(LOG_TAG, "readResponse exception occurs!", ex);
    }
    return exitStatus;
}
```

