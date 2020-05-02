---
title: Android ListView 与 RecyclerView 缓存机制
date: 2017-12-18 14:42:33
categories:
- 源码分析
tags:
- Android
- source code
---
> 通过研究 RecyclerView 和 ListView 二者的缓存机制，并得到了一些较有益的“结论”。

<!--more-->

## ListView

两级缓存：`mActiveViews`、`mScrapView`

ListView 中创建对象的个数 = 屏幕显示的条目数 + 1

## RecyclerView

四级缓存：`mAttachedScrap`、`mCachedViews`、`mRecyclerPool`、`mViewCacheExtension`（自定义）

当只有一种类型的 item view 的情况下，缓存创建的 ViewHolder 的个数为屏幕最多显示 item view 的个数+2。

当有多种类型的 item view 在 RecyclerView 中显示，每种类型的 item view 缓存创建的 ViewHolder 个数为其在屏幕中最多显示 item view 的个数 + 1。

## 对比差异

### 相同点：

1. `mActiveViews`和`mAttachedScrap`功能相似，意义在于快速重用屏幕上可见的列表项 ItemView，而不需要重新 createView 和 bindView。
2. `mScrapView`和`mCachedViews` + `mReyclerViewPool`功能相似，意义在于缓存离开屏幕的 ItemView，目的是让即将进入屏幕的 ItemView 重用。

### 不同点：

1.  ListView 缓存 View，通过 pos 获取的是 view，根据 pos 获取相应的缓存后，即使数据源数据不变，仍然会重新 bindView。
2.  RecyclerView 缓存 RecyclerView.ViewHolder，通过 pos 获取的是 viewholder。根据 pos 获取相应的缓存后，当数据源数据不变时，无须重新 bindView。

|           | AbsListView | RecyclerView |
| :-------: | :---------: | :----------: |
|   缓存    |    View     |  Viewholder  |
| 定向刷新  |   不支持    |     支持     |
| 局部刷新  |   不支持    |     支持     |
| 刷新动画  |   不支持    |     支持     |
| Item 点击 |    支持     |    不支持    |
|  分隔线   |  样式单一   |  自定义样式  |
| 布局方式  |  列表/网格  |  自定义样式  |
| 头尾添加  |    支持     |    不支持    |



### RecyclerView的优势

1. `mCacheViews`的使用，可以做到屏幕外的列表项 ItemView 进入屏幕内时也无须 bindView 快速重用。
2. `mRecyclerPool`可以供多个 RecyclerView 共同使用，在特定场景下，如 viewpaper + 多个列表页下有优势。

## 局部刷新

ListView 和 RecyclerView 最大的区别在于数据源改变时的缓存的处理逻辑，ListView 是“一锅端”，将所有的`mActiveViews`都移入了二级缓存`mScrapViews`，而 RecyclerView 则是更加灵活地对每个 View 修改标志位，区分是否重新 bindView。