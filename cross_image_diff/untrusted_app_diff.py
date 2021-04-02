
import os
import pickle
import logging
import argparse
import networkx as nx

from image import *

from difflib import Differ

logging.basicConfig(format="%(asctime)s:%(name)s:%(levelname)s:%(message)s")
logging.getLogger().setLevel(logging.CRITICAL)

logging.getLogger("image").setLevel(logging.ERROR)

log = logging.getLogger("cross_image_diff")
log.setLevel(logging.DEBUG)

logging.getLogger("process").setLevel(logging.WARNING)

def main(aosp_img, oem_img, filter_ipc):
    log.info("Initializing AOSP Image...")
    aosp_img = Image(aosp_img)
    log.info("Initializing OEM Image...")
    oem_img = Image(oem_img)

    ua_name = "process:untrusted_app"

    aosp_ua = aosp_img.resolve_proc_name(ua_name)[0]
    oem_ua = oem_img.resolve_proc_name(ua_name)[0]

    aosp_ua_writable = aosp_img.query(aosp_ua, QUERY_WILDCARD, 2)
    oem_ua_writable = oem_img.query(oem_ua, QUERY_WILDCARD, 2)

    oem_extra = full_diff(aosp_ua_writable, oem_ua_writable, "right")
    # filter redundant paths
    to_remove = []
    for p1 in oem_extra:
    	if p1.count("->") == 1:
    		for p2 in oem_extra:
    			if p2.startswith(p1) and p2 != p1:
    				to_remove.append(p1)

    oem_extra = [p for p in oem_extra if p not in to_remove]

    print("\n".join(oem_extra))    
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

    args = parser.parse_args()
    exit(main(**vars(args)))

