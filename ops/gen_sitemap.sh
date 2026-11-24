#!/usr/bin/env bash
# 生成静态站与博客的 sitemap.xml（数据来自 Typecho 数据库）
set -euo pipefail

SITE_DIR=/opt/1panel/apps/openresty/openresty/www/sites/47.115.150.227/index
BLOG_DIR=/opt/1panel/apps/typecho/blog/data
BASE=http://47.115.150.227
BASE_BLOG=http://47.115.150.227:40300
CONT=1Panel-mariadb-8VwW
CONF=/opt/1panel/apps/typecho/blog/data/config.inc.php

U=$(grep -oP "(?<=user' => ')\K[^']+" "$CONF" | head -1 || true)
P=$(grep -oP "(?<=password' => ')\K[^']+" "$CONF" | head -1 || true)
N=$(grep -oP "(?<=database' => ')\K[^']+" "$CONF" | head -1 || true)
R=$(grep -oP "(?<=prefix' => ')\K[^']+" "$CONF" | head -1 || true)
[ -n "$R" ] || R=typecho_

rows=$(docker exec "$CONT" mariadb -u"$U" -p"$P" "$N" -N -e \
  "select cid, slug, type, date_format(modified,'%Y-%m-%d') from ${R}contents where status='publish' and type in ('post','page') order by cid desc" 2>/dev/null)

emit() {
  local loc="$1" mod="$2"
  printf '  <url><loc>%s</loc>%s<changefreq>weekly</changefreq></url>\n' \
    "$loc" "${mod:+<lastmod>${mod}</lastmod>}"
}

# 静态站 sitemap：站点页面 + 博客文章，方便搜索引擎从一个入口发现
{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
  emit "$BASE/" ""
  emit "$BASE/status.html" ""
  emit "$BASE/rss.html" ""
  while IFS=$'\t' read -r cid slug type mod; do
    [ -n "$cid" ] || continue
    if [ "$type" = post ]; then
      emit "$BASE_BLOG/index.php/archives/$cid/" "$mod"
    else
      emit "$BASE_BLOG/$slug.html" "$mod"
    fi
  done <<< "$rows"
  echo '</urlset>'
} > "$SITE_DIR/sitemap.xml"

# 博客侧 sitemap：本站文章与独立页面
{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
  emit "$BASE_BLOG/" ""
  while IFS=$'\t' read -r cid slug type mod; do
    [ -n "$cid" ] || continue
    if [ "$type" = post ]; then
      emit "$BASE_BLOG/index.php/archives/$cid/" "$mod"
    else
      emit "$BASE_BLOG/$slug.html" "$mod"
    fi
  done <<< "$rows"
  echo '</urlset>'
} > "$BLOG_DIR/sitemap.xml"

echo "sitemap ok: 静态 $(grep -c '<url>' "$SITE_DIR/sitemap.xml") 条 / 博客 $(grep -c '<url>' "$BLOG_DIR/sitemap.xml") 条"
