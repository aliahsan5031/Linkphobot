"""
file_manager.py
===============
Linkphobot - Phase 7: Export System
File & Folder Management System

Handles:
- Output directory creation
- Smart filename generation
- File collision handling
- Export manifest (JSON index)
- Cleanup utilities
- File size reporting
"""

import os
import re
import json
import shutil
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass, field, asdict


# ════════════════════════════════════════════════════════════════════════════
# DIRECTORY STRUCTURE
# ════════════════════════════════════════════════════════════════════════════

DEFAULT_OUTPUT_ROOT = "outputs"

FOLDER_STRUCTURE = {
    "root":     "{output_root}",
    "linkedin": "{output_root}/linkedin",
    "web":      "{output_root}/web",
    "thumbs":   "{output_root}/thumbs",
    "print":    "{output_root}/print",
    "metadata": "{output_root}/metadata",
    "archive":  "{output_root}/archive",
}


def build_folder_structure(output_root: str = DEFAULT_OUTPUT_ROOT) -> dict:
    """
    Create all output subdirectories.

    Returns:
        dict mapping folder name -> absolute path
    """
    paths = {}
    for key, template in FOLDER_STRUCTURE.items():
        path = template.replace("{output_root}", output_root)
        os.makedirs(path, exist_ok=True)
        paths[key] = os.path.abspath(path)
    return paths


def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist. Returns absolute path."""
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


# ════════════════════════════════════════════════════════════════════════════
# FILENAME GENERATOR
# ════════════════════════════════════════════════════════════════════════════

def sanitize_filename(text: str, max_len: int = 40) -> str:
    """
    Convert any string into a safe, clean filename component.

    - Lowercase
    - Spaces and special chars -> underscores
    - No consecutive underscores
    - Max length enforced
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s\-]+', '_', text)
    text = re.sub(r'_+', '_', text)
    text = text.strip('_')
    return text[:max_len]


def generate_filename(topic:        str,
                       preset_name:  str = "linkedin",
                       page_num:     int = 0,
                       suffix:       str = "",
                       extension:    str = "png",
                       timestamp:    bool = True) -> str:
    """
    Generate a structured export filename.

    Format: {topic_slug}_{preset}{_pN}{suffix}{_timestamp}.{ext}

    Examples:
        ai_healthcare_linkedin.png
        ai_healthcare_linkedin_p2.png
        ai_healthcare_hq_20250115_143022.png

    Args:
        topic       : raw topic string
        preset_name : export preset name
        page_num    : carousel page number (0 = no page suffix)
        suffix      : additional suffix (e.g. "_v2")
        extension   : file extension without dot
        timestamp   : include timestamp in filename

    Returns:
        filename string
    """
    slug    = sanitize_filename(topic)
    preset  = sanitize_filename(preset_name)
    page    = f"_p{page_num}" if page_num > 0 else ""
    ts      = "_" + datetime.now().strftime("%Y%m%d_%H%M%S") if timestamp else ""
    ext     = extension.lower().lstrip(".")

    return f"{slug}_{preset}{page}{suffix}{ts}.{ext}"


def generate_batch_filenames(topic:       str,
                              n_pages:     int,
                              preset_name: str = "linkedin",
                              extension:   str = "png") -> List[str]:
    """
    Generate filenames for all pages of a carousel export.

    Returns:
        list of filename strings
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug   = sanitize_filename(topic)
    preset = sanitize_filename(preset_name)

    if n_pages == 1:
        return [f"{slug}_{preset}_{ts}.{extension}"]

    return [f"{slug}_{preset}_p{i+1}_{ts}.{extension}"
            for i in range(n_pages)]


def resolve_output_path(output_dir:   str,
                         filename:     str,
                         overwrite:    bool = True) -> str:
    """
    Resolve final output path, handling collisions.

    If overwrite=False and file exists, appends _v2, _v3 etc.

    Returns:
        absolute path string
    """
    full = os.path.join(output_dir, filename)

    if overwrite or not os.path.exists(full):
        return os.path.abspath(full)

    # Collision avoidance
    name, ext = os.path.splitext(filename)
    version   = 2
    while os.path.exists(full):
        full = os.path.join(output_dir, f"{name}_v{version}{ext}")
        version += 1

    return os.path.abspath(full)


# ════════════════════════════════════════════════════════════════════════════
# EXPORT RESULT
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ExportResult:
    """Record of a single exported file."""
    filepath:       str
    filename:       str
    preset_name:    str
    format:         str
    width:          int
    height:         int
    file_size_kb:   float
    page_num:       int = 0
    export_time_s:  float = 0.0
    success:        bool = True
    error:          str = ""

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size_kb / 1024, 3)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExportBatch:
    """Collection of ExportResults for one export job."""
    topic:          str
    generated_at:   str
    results:        List[ExportResult] = field(default_factory=list)
    total_time_s:   float = 0.0
    success_count:  int = 0
    error_count:    int = 0

    def add(self, result: ExportResult):
        self.results.append(result)
        if result.success:
            self.success_count += 1
        else:
            self.error_count += 1

    @property
    def all_paths(self) -> List[str]:
        return [r.filepath for r in self.results if r.success]

    @property
    def linkedin_paths(self) -> List[str]:
        return [r.filepath for r in self.results
                if r.success and r.preset_name in ("linkedin","linkedin_hq")]

    def to_dict(self) -> dict:
        return {
            "topic":         self.topic,
            "generated_at":  self.generated_at,
            "total_time_s":  self.total_time_s,
            "success_count": self.success_count,
            "error_count":   self.error_count,
            "results":       [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def print_summary(self):
        print("\n=== EXPORT SUMMARY ===")
        print(f"  Topic:    {self.topic[:50]}")
        print(f"  Exported: {self.success_count} file(s)")
        print(f"  Errors:   {self.error_count}")
        print(f"  Time:     {self.total_time_s}s")
        print()
        for r in self.results:
            status = "OK" if r.success else "FAIL"
            print(f"  [{status}] {r.filename}  ({r.file_size_kb:.0f} KB  {r.width}x{r.height})")
        print()


# ════════════════════════════════════════════════════════════════════════════
# EXPORT MANIFEST
# ════════════════════════════════════════════════════════════════════════════

def save_manifest(batch: ExportBatch, output_dir: str) -> str:
    """
    Save export manifest JSON alongside the exported files.

    Returns:
        path to saved manifest file
    """
    slug     = sanitize_filename(batch.topic)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{slug}_manifest_{ts}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(batch.to_json())

    return os.path.abspath(filepath)


def load_manifest(filepath: str) -> dict:
    """Load an export manifest JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ════════════════════════════════════════════════════════════════════════════
# FILE SIZE UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def get_file_size_kb(filepath: str) -> float:
    """Return file size in KB."""
    if not os.path.exists(filepath):
        return 0.0
    return round(os.path.getsize(filepath) / 1024, 2)


def get_directory_size_mb(directory: str) -> float:
    """Return total size of all files in directory in MB."""
    total = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return round(total / (1024 * 1024), 3)


def list_exports(output_dir: str,
                  extensions: tuple = (".png", ".jpg", ".jpeg", ".webp")) -> List[dict]:
    """
    List all exported image files in a directory.

    Returns:
        list of dicts with filename, size_kb, modified
    """
    if not os.path.isdir(output_dir):
        return []

    results = []
    for fname in sorted(os.listdir(output_dir)):
        if fname.lower().endswith(extensions):
            fpath = os.path.join(output_dir, fname)
            results.append({
                "filename":  fname,
                "filepath":  os.path.abspath(fpath),
                "size_kb":   get_file_size_kb(fpath),
                "modified":  datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat(),
            })
    return results


# ════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ════════════════════════════════════════════════════════════════════════════

def cleanup_old_exports(output_dir: str,
                         keep_latest: int = 10,
                         extensions: tuple = (".png",".jpg",".jpeg",".webp")) -> int:
    """
    Delete oldest export files, keeping only the `keep_latest` most recent.

    Returns:
        number of files deleted
    """
    files = list_exports(output_dir, extensions)
    files_sorted = sorted(files, key=lambda x: x["modified"], reverse=True)
    to_delete    = files_sorted[keep_latest:]
    deleted      = 0

    for f in to_delete:
        try:
            os.remove(f["filepath"])
            deleted += 1
        except OSError:
            pass

    return deleted


def archive_exports(output_dir: str, archive_dir: str) -> str:
    """
    Move all PNG/JPG files from output_dir to archive_dir with timestamp folder.

    Returns:
        path to archive folder created
    """
    ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(archive_dir, f"archive_{ts}")
    os.makedirs(archive_path, exist_ok=True)

    moved = 0
    for fname in os.listdir(output_dir):
        if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            src = os.path.join(output_dir, fname)
            dst = os.path.join(archive_path, fname)
            shutil.move(src, dst)
            moved += 1

    return archive_path
