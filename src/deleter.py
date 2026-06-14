"""
Deletion Tool Module
Instead of permanently deleting files, moves approved files into a
local "deleted/" recycle folder, preserving relative paths to avoid
name collisions and to allow easy restoration.
"""

import os
import shutil


def move_to_recycle(file_path, recycle_root="deleted", source_root=None):
    """
    Move a file into the recycle folder.

    If source_root is provided, the file's path relative to source_root
    is preserved inside recycle_root, so files from different subfolders
    don't collide and can be restored to their original location.

    Returns the new path of the moved file.
    """
    os.makedirs(recycle_root, exist_ok=True)

    if source_root:
        rel_path = os.path.relpath(file_path, source_root)
    else:
        rel_path = os.path.basename(file_path)

    dest_path = os.path.join(recycle_root, rel_path)
    dest_dir = os.path.dirname(dest_path)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    # Avoid overwriting an existing file in recycle bin
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(dest_path)
        counter = 1
        new_dest = f"{base}_{counter}{ext}"
        while os.path.exists(new_dest):
            counter += 1
            new_dest = f"{base}_{counter}{ext}"
        dest_path = new_dest

    shutil.move(file_path, dest_path)
    return dest_path


def permanently_delete(file_path):
    """
    Permanently delete a file. Used only if the user explicitly
    enables 'permanent delete' mode in the UI.
    """
    os.remove(file_path)
    return file_path


def restore_from_recycle(recycle_path, original_path):
    """
    Move a file from the recycle folder back to its original location.
    """
    dest_dir = os.path.dirname(original_path)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
    shutil.move(recycle_path, original_path)
    return original_path
