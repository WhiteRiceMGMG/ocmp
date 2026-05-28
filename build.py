from pathlib import Path
import markdown
import shutil
import re

from jinja2 import Environment, FileSystemLoader

CONTENT_DIR = Path("content")
OUTPUT_DIR = Path("public")
STATIC_DIR = Path("static")

# Jinja2
env = Environment(
    loader=FileSystemLoader("templates")
)

article_template = env.get_template("article.html")
index_template = env.get_template("index.html")

# カテゴリ一覧（テンプレート名と出力ディレクトリ名を一致させる）
CATEGORIES = ["daily", "dev", "gadget", "unctgr"]

# public初期化
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)

OUTPUT_DIR.mkdir()

# staticコピー
shutil.copytree(
    STATIC_DIR,
    OUTPUT_DIR,
    dirs_exist_ok=True
)

# markdown一覧
md_files = list(CONTENT_DIR.rglob("*.md"))

articles = []

# wikiリンク変換
def convert_links(text):
    pattern = r"\[\[(.*?)\]\]"

    def repl(match):
        name = match.group(1)
        return f'<a href="{name}.html">{name}</a>'

    return re.sub(pattern, repl, text)

# 記事生成
for md_file in md_files:
    raw = md_file.read_text(encoding="utf-8")
    raw = convert_links(raw)

    # title取得（デフォルトはファイル名）
    title = md_file.stem
    for line in raw.splitlines():
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
            break

    # markdown → html
    html_content = markdown.markdown(raw)

    # 相対パス
    relative_path = md_file.relative_to(CONTENT_DIR)

    # category（例: gadget, daily, dev, unctgr）
    category = relative_path.parent.name  # parent が '.' の場合は '' になる

    # filename
    filename = md_file.stem

    # 出力先
    output_dir = OUTPUT_DIR / category if category else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{filename}.html"

    # HTML生成
    final_html = article_template.render(
        title=title,
        content=html_content
    )

    output_path.write_text(final_html, encoding="utf-8")

    print(f"Generated: {output_path}")

    # index用（category を文字列で保持）
    articles.append({
        "title": title,
        "url": str(relative_path.with_suffix(".html")),
        "source": md_file,
        "category": category
    })

# 新着順（更新日時）
articles.sort(
    key=lambda x: x["source"].stat().st_mtime,
    reverse=True
)

# 最大20件（トップページ用）
top_articles = articles[:20]

# index生成
final_index = index_template.render(
    title="Home",
    articles=top_articles
)

(OUTPUT_DIR / "index.html").write_text(final_index, encoding="utf-8")
print("Generated: public/index.html")

# --- カテゴリページ生成 ---
# 各カテゴリごとにテンプレートを読み、該当カテゴリの記事を新着順で表示する
for cat in CATEGORIES:
    # フィルタ（category フィールドが一致するもの）
    cat_articles = [a for a in articles if a.get("category") == cat]

    # 新着順にして最大20件（必要なら数を変える）
    cat_articles.sort(key=lambda x: x["source"].stat().st_mtime, reverse=True)
    cat_articles = cat_articles[:20]

    # テンプレート読み込み（templates/<cat>.html が存在する前提）
    try:
        cat_template = env.get_template(f"{cat}.html")
    except Exception as e:
        # テンプレートがない場合は簡易テンプレートで代替（安全策）
        from jinja2 import Template
        fallback = """{% extends "base.html" %}{% block content %}
<h1>{{ title }}</h1>
<ul class="article-list">
{% for article in articles %}
  <li><a href="{{ article.url }}">{{ article.title }}</a></li>
{% else %}
  <li>記事がありません。</li>
{% endfor %}
</ul>
{% endblock %}"""
        cat_template = Template(fallback)

    # 出力先ディレクトリを確保
    out_dir = OUTPUT_DIR / cat
    out_dir.mkdir(parents=True, exist_ok=True)

    # レンダリング
    final_cat = cat_template.render(
        title=cat.upper(),
        articles=cat_articles
    )

    out_path = out_dir / f"{cat}.html"
    out_path.write_text(final_cat, encoding="utf-8")
    print(f"Generated category page: {out_path}")
