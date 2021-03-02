
import os
import pickle
import logging
import argparse
import networkx as nx

from image import *

from difflib import Differ

from config import *

logging.basicConfig(format="%(asctime)s:%(name)s:%(levelname)s:%(message)s")
logging.getLogger().setLevel(logging.CRITICAL)

logging.getLogger("image").setLevel(logging.ERROR)

log = logging.getLogger("cross_image_diff")
log.setLevel(logging.DEBUG)

logging.getLogger("process").setLevel(logging.WARNING)

def main(aosp_img, oem_img, filter_ipc, top, strength):
    log.info("Initializing AOSP Image...")
    aosp_img = Image(aosp_img)
    log.info("Initializing OEM Image...")
    oem_img = Image(oem_img)

    log.info("Finding top %d strongest processes by %s in AOSP image..." % (top, strength))
    aosp_strongest_procs = aosp_img.query_all_proc_strengths(sort_by=strength)[:top]
    # print("\n".join("%s %d" % (name, details[NOBJ_IX]) for name, details in aosp_strongest_procs))

    # log.info("Finding strongest processes in OEM image")
    # oem_strongest_procs = oem_img.query_all_proc_strengths(sort_by=NOBJ_IX)[:ntop]
    # print("\n".join("%s %d" % (name, details[NOBJ_IX]) for name, details in oem_strongest_procs))

    for proc, _ in aosp_strongest_procs:
        log.info("Finding attack surface for %s in AOSP image..." % proc)
        aosp_attack_surface, aosp_as_summary = aosp_img.query_attack_surface(proc)
        proc = aosp_img.strip_proc_pid(proc)
        log.info("Finding attack surface for %s in OEM image..." % proc)
        try:
            oem_proc_names = oem_img.resolve_proc_name(proc)
            oem_proc_name = oem_proc_names.pop()
            if oem_proc_names:
                log.warning("Found multiple names for %s: %s. Using %s..." % (proc, str(oem_proc_names), oem_proc_name))
        except KeyError as e:
            log.error("%s does not exist in OEM image, skipping..." % str(e))
            continue

        oem_attack_surface, oem_as_summary = oem_img.query_attack_surface(oem_proc_name)

        log.info("Performing IPC diff for %s" % proc)
        if filter_ipc:
            aosp_attack_surface = [path for path in aosp_attack_surface if path[1].get_obj_type() == "ipc"]
            oem_attack_surface = [path for path in oem_attack_surface if path[1].get_obj_type() == "ipc"]

        res = ipc_diff(aosp_attack_surface, oem_attack_surface, "right")
        print("****** %s Attack Surface Diff ******" % proc)
        print("\n".join(res))
        print()

    return 0

def render_path(path, start=None, end=None):
    
    if start:
        trimmed_path = path[start:]
    else:
        trimmed_path = path
        start = 0
    
    if end:
        if end <= start:
            raise ValueError("end must be greater than start")
        
        trimmed_path = trimmed_path[:(end - start)]

    rendered_path = []
    for obj in trimmed_path:
        name = obj.get_node_name()
        if obj.get_obj_type() == "process":
            name = name.replace("_%d" % obj.pid, "")

        rendered_path.append(name)

    return " -> ".join(rendered_path)

def diff(list1, list2, filter_param=""):
    d = Differ()

    result = d.compare(list1, list2)

    result = list(filter(lambda x: not x.startswith('? '), result))

    if filter_param == "left":
        result = list(filter(lambda x: x.startswith('- '), result))
    elif filter_param == "right":
        result = list(filter(lambda x: x.startswith('+ '), result))
    elif filter_param == "both":
        result = list(filter(lambda x: x.startswith('  '), result))

    return result

def ipc_diff(query1, query2, filter_param="", return_rendered=True):
    result = []

    diff_a_paths = dict([(render_path(x, end=2), x) for x in query1])
    diff_b_paths = dict([(render_path(x, end=2), x) for x in query2])

    result = diff(list(diff_a_paths.keys()), list(diff_b_paths.keys()), filter_param)

    if not return_rendered:
        result = [diff_a_paths.get(r[2:], diff_b_paths[r[2:]]) for r in result]

    return result

def full_diff(query1, query2, filter_param="", return_rendered=True):
    result = []

    d = Differ()

    diff_a_paths = dict([((render_path(x)), x) for x in query1])
    diff_b_paths = dict([((render_path(x)), x) for x in query2])

    result = diff(list(diff_a_paths.keys()), list(diff_b_paths.keys()), filter_param)

    if not return_rendered:
        result = [diff_a_paths.get(r[2:], diff_b_paths[r[2:]]) for r in result]

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Perform IPC diff for the strongest processes\' attack surface')

    parser.add_argument('aosp_img', help="Path to the AOSP image")
    parser.add_argument('oem_img', help="Path to the OEM image")

    parser.add_argument('--filter_ipc', action="store_true", help="Return only IPC objects (default=False)")
    parser.add_argument('--top', type=int, default=5, help="Number of top processes to diff (default=5)")
    parser.add_argument('--strength', default="nobj", help="Criteria to determine top processes. One of %s (default='nobj')" % list(Image.strength.keys()))

    args = parser.parse_args()
    exit(main(**vars(args)))




