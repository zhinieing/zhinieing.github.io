---
title: Android AOP
date: 2018-03-16 14:28:19
categories:
- 程序设计
tags:
- Android
- AOP
---
> Android AOP 就是通过预编译方式和运行期动态代理实现程序功能的统一维护的一种技术。利用 AOP 可以对业务逻辑的各个部分进行隔离，从而使得业务逻辑各部分之间的耦合度降低，提高程序的可重用性，提高开发效率。

<!--more-->

## Android AOP 之 APT、AspectJ、Javasisst

## APT

代表框架：DataBinding、Dagger2、ButterKnife、EventBus3、DBFlow、AndroidAnnotation

APT(`Annotation Processing Tool`)定义编译期的注解，再通过继承`Proccesor`实现代码生成逻辑，实现了编译期生成代码的逻辑。

使用姿势 ：

1. 建立一个 java 的 Module，写一个继承`AbstractProcessor`的类。
2. 在工具类里处理我们自定义的注解、生成代码。
3. 在 Gradle 中添加`dependencies annotationProcessor project(':apt')`。



## AspectJ

代表框架： Hugo(Jake Wharton)

**AspectJ** 支持编译期和加载时代码注入，在开始之前，我们先看看需要了解的词汇：

**Advice（通知）:** 典型的 Advice 类型有 before、after 和 around，分别表示在目标方法执行之前、执行后和完全替代目标方法执行的代码。

**Joint point（连接点）:** 程序中可能作为代码注入目标的特定的点和入口。

**Pointcut（切入点）:** 告诉代码注入工具，在何处注入一段特定代码的表达式。

**Aspect（切面）:** Pointcut 和 Advice 的组合看做切面。例如，在本例中通过定义一个 pointcut 和给定恰当的 advice，添加一个了内存缓存的切面。

**Weaving（织入）:** 注入代码（advices）到目标位置（joint points）的过程。



![mage-20180331003218](../Android AOP/image-201803310032188.png)

使用姿势：

1. 建立一个 android lib Module，定义一个切片，处理自定义注解，和添加切片逻辑。
2. 自定义一个 gradle 插件，使用 AspectJ 的编译器（ajc，一个java编译器的扩展)，对所有受 aspect 影响的类进行织入，在 gradle 的编译 task 中增加额外配置，使之能正确编译运行。
3. 在 Gradle 中添加`apply plugin:com.app.plugin.AspectjPlugin`。



## Javassist

代表框架：热修复框架 HotFix 、Savior（InstantRun）等

Javassist 作用是在编译器间修改 class 文件，可以让我们直接修改编译后的 class 二进制代码，首先我们得知道什么时候编译完成，并且我们要赶在 class 文件被转化为 dex 文件之前去修改。使用`Transform`能很方便地实现，`Tranfrom`一经注册便会自动添加到 Task 执行序列中，并且正好是项目被打包成 dex 之前。

使用姿势：

1. 定义一个 buildSrc module 添加自定义 Plugin。
2. 自定义`Transform`。
3. 在`Transform`里处理 Task，通过 inputs 拿到一些东西，处理完毕之后就输出 outputs，而下一个 Task 的 inputs 则是上一个 Task 的 outputs。
4. 使用 Javassist 操作字节码，添加新的逻辑或者修改原有逻辑。
5. 在 Gradle 中添加`apply plugin:com.app.plugin.MyPlugin`。
