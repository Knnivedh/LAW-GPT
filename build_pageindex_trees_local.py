"""
PageIndex Tree Builder — Groq-Powered (FREE)
=============================================
Builds vectorless JSON tree indices for ALL statute .txt files using
the patched PageIndex open-source engine routed through Groq (llama-3.3-70b).

Usage:
    py build_pageindex_trees_local.py                 # process all
    py build_pageindex_trees_local.py --file IPC.txt  # process one file
    py build_pageindex_trees_local.py --list           # list existing trees
"""

from __future__ import annotations
import argparse, json, logging, os, sys, asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATUTES_DIR = ROOT.parent.parent / "BACKUP_DATA" / "DATA" / "Statutes"
TREES_DIR = ROOT / "PERMANENT_RAG_FILES" / "PAGEINDEX_TREES"
TREES_DIR.mkdir(parents=True, exist_ok=True)

# Add PageIndex to path
sys.path.insert(0, str(ROOT / "PageIndex"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("pageindex_builder")

# Model to use via Groq
GROQ_MODEL = "llama3.1-8b"


def txt_to_markdown(txt_path: Path) -> str:
    """Convert plain statute .txt into markdown with proper headings."""
    import re
    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    lines = text.split("\n")
    md_lines = []
    statute_name = txt_path.stem.replace("_", " ")
    md_lines.append(f"# {statute_name}\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            md_lines.append("")
            continue

        # PART / CHAPTER headings -> ##
        if re.match(r'^(PART|CHAPTER|SCHEDULE)\s', stripped, re.IGNORECASE):
            md_lines.append(f"\n## {stripped}\n")
        # Section headings -> ###
        elif re.match(r'^Section\s+\d+[A-Z]?\.', stripped, re.IGNORECASE):
            # Split: heading = "Section 302. Punishment for murder."
            # body follows on same line sometimes
            match = re.match(r'^(Section\s+\d+[A-Z]?\.\s*[^.]*\.?)(.*)', stripped, re.IGNORECASE)
            if match:
                heading = match.group(1).strip()
                body = match.group(2).strip()
                md_lines.append(f"\n### {heading}\n")
                if body:
                    md_lines.append(body)
            else:
                md_lines.append(f"\n### {stripped}\n")
        # Article headings (for some acts)
        elif re.match(r'^Article\s+\d+', stripped, re.IGNORECASE):
            md_lines.append(f"\n### {stripped}\n")
        # Act title lines (first few lines) -> keep as-is under the # heading
        elif re.match(r'^\(Act No\.', stripped):
            md_lines.append(f"*{stripped}*\n")
        else:
            md_lines.append(stripped)

    return "\n".join(md_lines)


def build_tree_from_txt(txt_path: Path, model: str = GROQ_MODEL) -> dict | None:
    """
    Build a PageIndex-style hierarchical tree from a plain .txt statute file.
    Converts to markdown first, then uses md_to_tree pipeline via Groq.
    """
    from pageindex.page_index_md import md_to_tree
    from pageindex.utils import ConfigLoader
    import tempfile

    logger.info(f"Building tree for: {txt_path.name} ({txt_path.stat().st_size // 1024} KB)")

    # Step 1: Convert TXT to Markdown
    logger.info("  Converting TXT -> Markdown ...")
    md_content = txt_to_markdown(txt_path)

    # Write temp .md file
    temp_md = txt_path.with_suffix(".md")
    with open(temp_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"  Temp markdown: {temp_md.name} ({len(md_content)} chars)")

    # Step 2: Run PageIndex md_to_tree
    config_loader = ConfigLoader()
    user_opt = {
        'model': model,
        'if_add_node_summary': 'yes',
        'if_add_doc_description': 'no',
        'if_add_node_text': 'no',
        'if_add_node_id': 'yes',
    }
    opt = config_loader.load(user_opt)

    try:
        tree = asyncio.run(md_to_tree(
            md_path=str(temp_md),
            if_thinning=False,
            min_token_threshold=5000,
            if_add_node_summary=opt.if_add_node_summary,
            summary_token_threshold=200,
            model=model,
            if_add_doc_description=opt.if_add_doc_description,
            if_add_node_text=opt.if_add_node_text,
            if_add_node_id=opt.if_add_node_id,
        ))
        return tree
    except Exception as e:
        logger.error(f"Failed to build tree for {txt_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temp markdown
        if temp_md.exists():
            temp_md.unlink()


def process_all_statutes(single_file: str | None = None):
    """Process all .txt files or a single file."""
    if single_file:
        target = STATUTES_DIR / single_file
        if not target.exists():
            logger.error(f"File not found: {target}")
            return
        files = [target]
    else:
        files = sorted(STATUTES_DIR.glob("*.txt"))

    logger.info(f"{'=' * 60}")
    logger.info(f"PageIndex Tree Builder (Groq: {GROQ_MODEL})")
    logger.info(f"Source: {STATUTES_DIR}")
    logger.info(f"Output: {TREES_DIR}")
    logger.info(f"Files to process: {len(files)}")
    logger.info(f"{'=' * 60}")

    success = 0
    failed = 0

    for i, fpath in enumerate(files, 1):
        output_file = TREES_DIR / f"{fpath.stem}_tree.json"

        if output_file.exists():
            logger.info(f"[{i}/{len(files)}] SKIP (already exists): {fpath.stem}")
            success += 1
            continue

        logger.info(f"\n[{i}/{len(files)}] Processing: {fpath.name}")

        tree = build_tree_from_txt(fpath)

        if tree:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(tree, f, indent=2, ensure_ascii=False)
            logger.info(f"  ✅ Saved tree -> {output_file.name}")
            success += 1
        else:
            logger.error(f"  ❌ Failed: {fpath.name}")
            failed += 1

    logger.info(f"\n{'=' * 60}")
    logger.info(f"COMPLETE: {success} succeeded, {failed} failed")
    logger.info(f"Trees saved in: {TREES_DIR}")
    logger.info(f"{'=' * 60}")


def list_trees():
    """List all existing tree files."""
    trees = sorted(TREES_DIR.glob("*_tree.json"))
    if not trees:
        print("No tree files found.")
        return
    print(f"\n{'=' * 50}")
    print(f"PageIndex Trees ({len(trees)} files)")
    print(f"{'=' * 50}")
    for t in trees:
        size = t.stat().st_size // 1024
        print(f"  {t.name}  ({size} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build PageIndex trees locally via Groq")
    parser.add_argument("--file", type=str, help="Process single file")
    parser.add_argument("--list", action="store_true", help="List existing trees")
    args = parser.parse_args()

    if args.list:
        list_trees()
    else:
        process_all_statutes(single_file=args.file)
