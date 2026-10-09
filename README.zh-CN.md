# Verbatim Guard

**AI 引用的这句话，原文里真的有吗？**

一个本地运行的 Python 库和命令行工具，用于检查引文、行号范围和原文指纹。不需要 API Key，不调用另一个模型，没有运行时第三方依赖。

[English](README.md) · [下载发行版](https://github.com/waiteddegree608-ship-it/verbatim-guard/releases) · [报告示例](https://github.com/waiteddegree608-ship-it/verbatim-guard/releases/download/v0.1.0/demo-report.html)

![原文中是 48 位参与者，AI 引文写成 480；检查结果为 NOT_FOUND。](docs/overview.svg)

适合已经拿到原文文本的 RAG、论文评审和写作工作流。**匹配到原文不代表事实正确，也不代表引文支持模型在上下文中提出的结论。**

## 一分钟试用

需要 Python 3.10 或以上。从 GitHub 安装版本固定的 wheel，不需要 Git：

```sh
python -m pip install "https://github.com/waiteddegree608-ship-it/verbatim-guard/releases/download/v0.1.0/verbatim_guard-0.1.0-py3-none-any.whl"
verbatim-guard demo --mode whitespace
```

演示包含 6 条引文：正确引文、改错数字、错误行号、重复文本、缺失文档，以及换行后仍可匹配的引文。结果是 **2 条通过，4 条需要处理**。演示故意包含错误，返回退出码 `1` 是正常结果。

生成可直接在浏览器打开的离线报告：

```sh
verbatim-guard demo --mode whitespace --format html --output report.html
```

报告会包含匹配到的原文片段，分享前请检查内容。本版本通过 GitHub Releases 分发，**尚未发布到 PyPI**。

也可以从源码安装：

```sh
git clone https://github.com/waiteddegree608-ship-it/verbatim-guard.git
cd verbatim-guard
python -m pip install .
verbatim-guard check examples/passing.json
```

## 接入现有程序

```python
from verbatim_guard import verify

source = "试验说明\n实验包含48名参与者。\n"
result = verify("实验包含48名参与者。", source, lines=(2, 2))
assert result.ok
print(result.status)  # EXACT
print(result.to_dict())
```

批量检查模型的结构化输出：

```python
from verbatim_guard import check_bundle

report = check_bundle({
    "sources": {"paper": "实验包含48名参与者。"},
    "claims": [{
        "id": "sample-size",
        "source": "paper",
        "quote": "实验包含480名参与者。"
    }]
})
assert not report["ok"]
assert report["results"][0]["status"] == "NOT_FOUND"
```

`sources` 的值是原文文本，键是文档标签。它们不是文件路径或 URL。`claims` 中的每项需要 `id`、`source`、`quote`，可选 `lines` 与 `source_sha256`。工具不会根据模型提供的文档标签打开文件或访问网址。

对于文件输入，把上面的结构保存为 UTF-8 JSON：

```sh
verbatim-guard check evidence.json --format json --output report.json
```

## 结果与退出码

| 状态 | 含义 | 通过 |
| --- | --- | --- |
| EXACT | 在允许范围内找到一个完全匹配 | 是 |
| WHITESPACE | 在显式启用的空白折叠模式下找到一个匹配 | 是 |
| NOT_FOUND | 找不到引文 | 否 |
| WRONG_LOCATION | 原文中存在，但不在指定行范围内 | 否 |
| AMBIGUOUS | 在允许范围内至少有两处匹配 | 否 |
| SOURCE_CHANGED | 原文指纹与提供的指纹不同 | 否 |
| MISSING_SOURCE | 文档标签不存在 | 否 |
| EMPTY_QUOTE | 引文为空或只有空白 | 否 |
| INVALID_LINES | 行范围倒置或越界 | 否 |

退出码 `0` 表示全部通过，`1` 表示至少一条检查未通过，`2` 表示输入格式或文件错误。重复 JSON 键、重复引文 ID、拼错的字段和空批次都会拒绝处理，避免误报全部通过。

## 重要约定

- 默认严格匹配，保留大小写、标点、Unicode 字符和空白；不做模糊匹配或省略号扩展。
- `--mode whitespace` 将连续 Unicode 空白折叠为一个空格，并忽略引文两端空白；不改变大小写、全半角、标点和重音形式。此模式会改变通过条件，需要主动开启。
- 行号从 1 开始，两端包含；偏移量按 Python Unicode 字符计数，从 0 开始，结束位置不包含。它不是字节位置，也不是 JavaScript UTF-16 位置。支持 LF、CRLF 和 CR，文末换行不额外算一行。
- 最多返回两处匹配；两处表示“至少两处”。给出较小的行范围可以消除重复文本的歧义。
- `fingerprint(source)` 对传入的文本按 UTF-8 编码后计算 SHA-256，保留换行。它不是原始 PDF 文件的哈希。应在最初提取证据时保存指纹，稍后对新文本核验；临检查前重新计算指纹无法发现历史变更。
- CLI 输入上限为 8 MiB，批次包含 1–100 个原文和 1–1,000 条引文；单条 Python API 的输入大小由调用方限制。

## 能力边界

不解析 PDF、不做 OCR、不联网检索、不检查 DOI 或撤稿状态，也不推理“原文是否支持整段结论”。PDF 文本提取错误可能使真实引文匹配失败；短语偶然出现也可能误导使用者，需要查看上下文。示例和测试是合成案例，不是实际论文集上的准确率评测。

相关工具及定位见[英文文档](README.md#related-work)。欢迎提供最小复现案例或实际集成经验。若工具有帮助，可以 star 收藏；不要提交私人文稿或凭据作为测试数据。

开发方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，采用 [MIT 许可证](LICENSE)。
