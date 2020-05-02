---
title: View 的事件分发机制
date: 2017-10-20 12:43:35
categories:
- 源码分析
tags:
- Android
- source code
---
> 在 Android 开发中，事件分发机制是一块 Android 比较重要的知识体系，了解并熟悉整套的分发机制有助于更好的分析各种点击滑动失效问题，更好去扩展控件的事件功能和开发自定义控件。

<!--more-->

**Tips：**

改变 View 的位置可以通过：
1. 使用动画
2. 改变布局参数


点击事件的分发过程由三个方法来共同完成，分别是：

> `dispatchTouchEvent`、`onInterceptTouchEvent`、`onTouchEvent`。


三者的关系可以用如下代码来表示：

```Java
public boolean dispatchTouchEvent(MotionEvent ev) {
    boolean consume = false;
    if (onInterceptTouchEvent(ev)) {
        consume = onTouchEvent(ev);
    } else {
        consume = child.dispatchTouchEvent(ev);
    }
    
    return consume;
}
```



## 点击事件的传递规则

1. 正常情况下，一个事件序列只能被一个 View 拦截且消耗。
2. 某个 View 一旦决定拦截，那么这一个事件序列都只能由它来处理（如果事件序到能够传递给它的话），并且它的`onlnterceptTouchEvent`不会再被调用。
3. 某个 View 一旦开始处理事件，如果它不消耗`ACTION_DOWN`事件（`onTouchEvent`返回了 false），那么同一事件序列中的其他事件都不会再交给它来处理，并且事件将重新交由它的父元素去处理，即父元素的`onTouchEvent`会被调用。
4. 如果 View 不消耗除`ACTION_DOWN`以外的其他事件，那么这个点击事件会消失，此时父元素的`onTouchEvent`并不会被调用，并且当前 View 可以持续收到后续的事件，最终这些消失的点击事件会传递给 Activity 处理。
5.  ViewGroup 默认不拦截任何事件，Android 源码中 ViewGroup 的`onInterceptTouchEvent`方法默认返回 false。
6. View 没有`onInterceptTouchEvent`方法，一旦有点击事件传递给它，那么它的`onTouchEvent`方法就会被调用。
7. View 的`onTouchEvent`默认都会消耗事件（返回 true），除非它是不可点击的（clickable 和 longClickable 同时为 false），View 的 longClickable 属性默认都为 false，clickable 属性要分情况，比如 Button 的 clickable 属性默认为 true，而 TextView 的 clickable 属性默认为 false。
8. View 的 enable 属性不影响`onTouchEvent`的默认返回值。哪怕一个 View 是 disable 状态的，只要它的 clickable 或者 longClickable 有一个为 true，那么它的`onTouchEvent`就返回 true。
9. onClick 会发生的前提是当前 View 是可点击的，并且它收到了 down 和 up 的事件。
10. 事件传递过程都是由外向内的，即事件总是先传递给父元素，然后再由父元素分发给子 View，通过`requestDisallowInterceptTouchEvent`方法可以在子元素中干预父元素的事件分发过程。但是`ACTION_DOWN`事件除外。



## 事件分发的源码解析

### Activity 对点击事件的分发过程

> Activity 的`dispatchTouchEvent`方法

```java
public boolean dispatchTouchEvent(MotionEvent ev) {
    if (ev.getAction() == MotionEvent.ACTION_DOWN) {
        onUserInteraction();
    }
    if (getWindow().superDispatchTouchEvent(ev)) {
        return true;
    }
    return onTouchEvent(ev);
}
```

首先事件开始交给 Activity 所附属的 Window 进行分发，如果返回 true，整个事件循环就结束了，返回 false 意味着事件没人处理，所有 View 的`onTouchEvent`返回了 false，那么 Activity 的`onTouchEvent`就会被调用。Window 的实例 PhoneWindow 将事件直接传递给了 DecorView。



### 顶级 View 对点击事件的分发过程

>  ViewGroup 的`dispatchTouchEvent`方法

```Java
final boolean intercepted;
if (actionMasked == MotionEvent.ACTION_DOWN
        || mFirstTouchTarget != null) {
    final boolean disallowIntercept = (mGroupFlags & FLAG_DISALLOW_INTERCEPT) != 0;
    if (!disallowIntercept) {
        intercepted = onInterceptTouchEvent(ev);
        ev.setAction(action); // restore action in case it was changed
    } else {
        intercepted = false;
    }
} else {
    // There are no touch targets and this action is not an initial down
    // so this view group continues to intercept touches.
    intercepted = true;
}
```

当事件类型为`ACTION_DOWN`或者`mFirstTouchTarget  != null`时会判断是否要拦截当前事件。当 ViewGroup 不拦截事件并将事件交给子元素处理时，`mFirstTouchTarget`会被赋值并指向子元素，`mFirstTouchTarget != null`。反过来，一旦事件由当前 ViewGroup 拦截，`mFirstTouchTarget  != null`就不成立，那么当`ACTION_MOVE`和`ACTION_UP`事件到来时，ViewGroup 的`onInterceptTouchEvent`不会在被调用，并且同一序列中的其他事件都会默认交给它处理。

这里要注意`FLAG_DISALLOW_INTERCEPT`标记位，它是通过`requestDisallowInterceptTouchEvent`方法来设置的，它一旦设置后，ViewGroup 将无法拦截除了`ACTION_DOWN`以外的其他点击事件。因为当面对`ACTION_DOWN`事件时，ViewGroup 总是会调用自己的`onInterceptTouchEvent`方法来询问是否要拦截事件，在下面的代码中，ViewGroup 也会在`ACTION_DOWN`事件到来时做重置状态的操作。

```java
if (actionMasked == MotionEvent.ACTION_DOWN) {
    cancelAndClearTouchTargets(ev);
    resetTouchState();
}
```

当 ViewGroup 不拦截事件时，事件会向下分发交给它的子 View 进行处理。



### View 对点击事件的处理过程

> View 的`dispatchTouchEvent`方法

```java
public boolean dispatchTouchEvent(MotionEvent event) {
    boolean result = false;
    ...
    if (onFilterTouchEventForSecurity(event)) {
        if ((mViewFlags & ENABLED_MASK) == ENABLED && handleScrollBarDragging(event)) {
            result = true;
        }
        //noinspection SimplifiableIfStatement
        ListenerInfo li = mListenerInfo;
        if (li != null && li.mOnTouchListener != null
                && (mViewFlags & ENABLED_MASK) == ENABLED
                && li.mOnTouchListener.onTouch(this, event)) {
            result = true;
        }

        if (!result && onTouchEvent(event)) {
            result = true;
        }
    }
    ...
    return result;
}
```

View 首先会判断有没有设置`OnTouchListener`，如果`OnTouchListener`中的`onTouch`方法返回 true，那么`onTouchEvent`就不会被调用，可见`OnTouchListener`的优先级高于`onTouchEvent`。

接下来再分析`onTouchEvent`的实现。当 View 处于不可用状态下时，也会消耗点击事件，尽管它看起来不可用。

```java
if ((viewFlags & ENABLED_MASK) == DISABLED) { 
	if (event.getAction() == MotionEvent.ACTION_UP &;&; (mPrivateFlags &; PFLAG_PRESSED) != 0) { 
		setPressed(false); 
	} 
    // A disabled view that is clickable still consumes the touch 
    // events, it just doesn't respond to them. 
	return (((viewFlags &; CLICKABLE) == CLICKABLE || (viewFlags &; LONG_CLICKABLE) == LONG_CLICKABLE)); 
} 
```

下面再看一下`onTouchEvent`中对点击事件的具体处理

```java
if (((viewFlags & CLICKABLE) == CLICKABLE || 
     (viewFlags & LONG_CLICKABLE) == LONG_CLICKABLE)) {
    switch (event.getAction()) {
        case MotionEvent.ACTION_UP:
            boolean prepressed = (mPrivateFlags & PREPRESSED) != 0;
            if ((mPrivateFlags & PRESSED) != 0 || prepressed) {
                ...
                if (!mHasPerformedLongPress) {
                    removeLongPressCallback();
                    if (!focusTaken) {
                        if (mPerformClick == null) {
                            mPerformClick = new PerformClick();
                        }
                        if (!post(mPerformClick)) {
                            performClick();
                        }
                    }
                }
                ...
            }
            break;
    }
    ...
    return true;
}
```

可见只要 View 的 CLICKABLE 和 LONG_CLICKABLE 有一个为 true，它就会消耗这个事件，即`onTouchEvent`方法返回 true。然后就是当`ACTION_UP`事件发生时，会触发`performClick`方法，如果 View 设置了`OnClickListener`，那么它的`onClick`方法会被调用。
