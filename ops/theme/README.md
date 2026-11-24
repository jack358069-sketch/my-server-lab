# G 主题改动记录（2026-11-24）

主题目录：`/opt/1panel/apps/typecho/blog/data/usr/themes/G`（宿主机路径）
容器内路径：`/app/usr/themes/G`

改动只涉及两个文件，均为"在原文中插入一小段"，母语保持原样，方便回滚。

## 1. `components/header.php`

在 `<title>` 之后插入一段 PHP + 两个 meta：

```php
<?php
$zlIsArticle = $this->is('post') || $this->is('page');
$zlImg = $zlIsArticle ? G::getArticleFieldsBanner($this) : G::$config['defaultBanner'];
if ($zlImg == 'none' || empty($zlImg)) {
    $zlImg = G::$config['defaultBanner'];
}
if (strpos($zlImg, 'http') !== 0) {
    $zlImg = 'http://47.115.150.227/' . ltrim($zlImg, '/');
}
?>
<meta property="og:image" content="<?php echo htmlspecialchars($zlImg, ENT_QUOTES, 'UTF-8'); ?>">
<meta name="twitter:image" content="<?php echo htmlspecialchars($zlImg, ENT_QUOTES, 'UTF-8'); ?>">
```

说明：
- Typecho 核心 `$this->header()` 已输出 canonical、description、og:title/description/url，
  这里只补它缺的分享图（og:image / twitter:image），避免重复标签。
- 图片统一指向静态站 `http://47.115.150.227/preset/bg/b*.svg`。

回滚：删掉这段即可。

## 2. `post.php`

在 `#post-footer` 之后插入上下篇导航：

```php
<div id="post-nav">
    <p class="post-nav-item"><?php $this->theNext('下一篇：%s', '下一篇：没有了'); ?></p>
    <p class="post-nav-item"><?php $this->thePrev('上一篇：%s', '上一篇：没有了'); ?></p>
</div>
<style> ...（圆角卡片样式，见线上文件）... </style>
```

## 3. 主题选项（数据库 `typecho_options` 中 `theme:G`）

- `enableDefaultTOC` 由 `0` 改为 `1`：启用主题自带 tocbot 目录
- `customFooterJS` 在原 personalization 加载器后追加 `preset/extra.js` 的加载器（**必须单行，不能插入换行**，否则 JSON 字符串含控制字符会导致全站 500）
- 修改方式：SQL `REPLACE(value, '旧串', '新串')`，不要整段重写 JSON（重写曾导致 500）

## 4. 附属脚本

- `/root/gen_sitemap.sh`（仓库 `ops/gen_sitemap.sh`）：每 6 小时生成：
  - 静态站 `/index/sitemap.xml`
  - 博客 `blog/data/sitemap.xml`
- `/etc/cron.d/zerolab-sitemap`（仓库 `ops/cron-zerolab-sitemap`）
- `/etc/cron.d/zerolab-stats`（仓库 `ops/cron-zerolab-stats`）：每小时用 GoAccess 生成 `/index/stats.html`（IP 已匿名化、排除爬虫）
- 博客 `robots.txt`（仓库 `ops/blog_robots.txt`）

## 5. 备用文件

线上主题目录里有 `components/header.php.new`（部署时的临时副本），可删。
