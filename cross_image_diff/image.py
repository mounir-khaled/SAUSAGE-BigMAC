
import os
import re
import sys
import time
import pickle
import logging
import networkx as nx
import subprocess as sp

sys.path.insert(1, os.path.join(sys.path[0], '..'))
import overlay

log = logging.getLogger(__name__)

QUERY_WILDCARD = "_"
QUERY_WILDCARD_AST = "*"

class NodeNotFoundException(Exception):
    pass

class MalformedResultException(Exception):
    pass

def _parse_result(result):
    if len(result) == 0:
        return []

    orig_result = result.decode()
    lines = orig_result.split("\n")

    if len(lines) < 5:
        raise MalformedResultException("result had less than 5 lines")

    result = lines[-1]

    # remove all whitespace
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'([a-zA-Z0-9]),([a-zA-Z0-9])', "\\1','\\2", result)
    result = re.sub(r'\[([a-zA-Z0-9])', r'[' + r"'\1", result)
    result = re.sub(r'([a-zA-Z0-9])\]', r'\1' + "'" + ']', result)

    try:
        res = eval(result)
    except SyntaxError:
        with open('bad-result', 'w') as fp:
            fp.write(orig_result)
        
        raise MalformedResultException("SyntaxError on eval, bad result dumped to %s" % 
                                            os.path.join(os.getcwd(), "bad-result"))
    return res

def exec_query(db_dir, start, end, cutoff, cap=None, source=None):
    if type(start) != str or type(end) != str:
        raise TypeError("expected str for start and end")

    if type(cutoff) != int:
        raise TypeError("expected int for cutoff")
    
    else:
        if cutoff <= 0: 
            raise ValueError("cutoff must be a positive integer (> 0)")

    cmdline = [start, end, str(cutoff)]

    binary = "inst3"
    if cap:
        cmdline += [cap]
        log.debug("Cap %s", cap)
        binary = "inst4"

    if source:
        cmdline += [source]
        log.debug("External Source %s", source)
        binary = "inst5"

    log.debug("executing '%s' args : %s", binary, cmdline)
    binary_path = os.path.join(db_dir, binary)
    proc = sp.Popen([binary_path] + cmdline, stdout=sp.PIPE)

    stime = time.time()
    try:
        stdout, stderr = proc.communicate()
    except KeyboardInterrupt as e:
        proc.kill()
        raise e

    etime = time.time()

    result = _parse_result(stdout)
    log.debug("Got %d paths in %.2f seconds", len(result), etime-stime)

    return result

class Image:

    strength = {
        "NTYPE": 0,
        "NOBJ": 1,
        "NIPC": 2,
        "NFILE": 3,
        "CD_STRENGTH": 4
        }

    def __init__(self, path, generate_files=True):
        self.db_path = os.path.join(path, "db")

        img_path = os.path.normpath(os.path.join(self.db_path, os.pardir))
        vendor_path, self.name = os.path.split(img_path)
        policy_path, self.vendor = os.path.split(vendor_path)

        self.generate_db_files()
        self.inst = self.load_inst()
        self.node_objs = self.load_node_objs(self.inst)
        self.node_id_map = self.load_node_map()
        self.node_id_map_inv = dict([[v,k] for k,v in self.node_id_map.items()])

    def generate_db_files(self):
        # Delete previously generated inst files
        do_not_delete = {"policy_files.db", "filesystems.db"}
        files_in_db = os.listdir(self.db_path)
        for f in files_in_db:
            if f in do_not_delete:
                continue

            path = os.path.join(self.db_path, f)
            if os.path.isfile(path):
                os.remove(path)

        # Generate new ones
        bigmac_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)) # ./cross_image_diff/..
        process_path = os.path.join(bigmac_dir, "process.py")

        process_args = [process_path, "--vendor", self.vendor, self.name, "--save", "--compile-prolog"]
        log.info(process_args)
        sp.run(process_args, cwd=bigmac_dir, stdout=sp.DEVNULL, stderr=sp.DEVNULL)

        # Check if everything is ok now
        should_exist = {"inst", "inst2", "inst3", "inst4", "inst5", "inst-map", "facts.pl"}
        files_in_db = os.listdir(self.db_path)
        if any(f not in files_in_db for f in should_exist):
            raise Exception("Failed to generate files!!")


    def load_inst(self):
        inst_path = os.path.join(self.db_path, "inst")
        with open(inst_path, 'rb') as fp:
            inst = pickle.load(fp)

        return inst

    def load_node_objs(self, inst):
        G = inst.fully_instantiate()
        return nx.get_node_attributes(G, 'obj')

    def load_node_map(self):
        inst_map_path = os.path.join(self.db_path, "inst-map")
        with open(inst_map_path, 'rb') as fp:
            node_id_map = pickle.load(fp)

        return node_id_map

    def get_obj_by_id(self, obj_id):
        return self.node_objs[self.node_id_map_inv[obj_id]]

    def retrieve_objs_in_query_result(self, paths):
        result = []
        for path in paths:
            try:
                path_objs = [self.get_obj_by_id(obj_id) for obj_id in path]
            except KeyError as e:
                log.warning("Could not find component %s in node_id_map" % str(e))
                continue

            result.append(path_objs)

        return result

    def strip_proc_pid(self, proc_name):
        obj = self.node_objs[proc_name]
        return proc_name.replace("_%d" % obj.pid, "")

    def resolve_proc_name(self, proc_name):
        # expecting e.g. process:system_server
        matches = []
        for proc in self.node_id_map.keys():
            if proc.startswith(proc_name):
                matches.append(proc)

        if not matches:
            raise KeyError(proc_name)

        return matches

    def query(self, start, end, cutoff, *args):
        WILDCARDS = [QUERY_WILDCARD, QUERY_WILDCARD_AST]

        if start in WILDCARDS:
            plstart = start
        else:
            plstart = self.node_id_map[start]

        if end in WILDCARDS:
            plend = end
        else:
            plend = self.node_id_map[end]

        log.debug("Query <%s> -> <%s> (cutoff %s)", start, end, cutoff)

        result = exec_query(self.db_path, plstart, plend, cutoff, *args)
        # show the shortest (easiest) paths first
        result = sorted(result, key=lambda x: len(x))
        return self.retrieve_objs_in_query_result(result)

    def load_query(self, filename):
        saved_queries_path = os.path.join(self.db_path, "saved_queries", filename)
        with open(saved_queries_path, 'rb') as fp:
            paths = pickle.load(fp)

        return self.retrieve_objs_in_query_result(paths)

    def query_attack_surface(self, target):
        all_writing_paths = self.query(QUERY_WILDCARD, target, 2)
        writable_writing_paths = [path for path in all_writing_paths if len(path) == 3]

        uniq_procs = set()
        uniq_ipc = set()
        uniq_types = set()
        uniq_files = set()
        uniq_obj = set()

        for path in writable_writing_paths:
            writing_obj = path[0]
            writeable_obj = path[1]

            uniq_obj.add(writeable_obj)
            uniq_types.add(writeable_obj.sid.type)

            if isinstance(writeable_obj, overlay.IPCNode):
                uniq_ipc.add(writeable_obj)
            elif isinstance(writeable_obj, overlay.FileNode):
                uniq_files.add(writeable_obj)

            if isinstance(writing_obj, overlay.ProcessNode): 
                uniq_procs.add(writing_obj)

        summary = {"ntype": len(uniq_types),
                    "nobj": len(uniq_obj),
                    "ipc": len(uniq_ipc),
                    "file": len(uniq_files),
                    "procs": len(uniq_procs),
                }

        return writable_writing_paths, summary

    def query_all_proc_strengths(self, sort_by):
        results = {}
        sort_by = Image.strength[sort_by.upper()]
        type_freq = {}
        # frequency of occurence of an object type
        # might be interesting to use this as an indicator of strength
        # then sort objects by the combined strength of the types it has access to
        # intuitively types with less objects that can access them are stronger...
        intermediate_results = {}
        for pn, p in self.inst.processes.items():
            name = p.get_node_name()
            try:
                result = self.query(name, QUERY_WILDCARD, 1)
            except KeyError as e:
                log.warning("could not find %s in node_id_map" % str(e))
                continue

            uniq_types = set()
            obj_types = {"ipc": [], "file": []}

            for path in result:
                obj = path[1]
                if obj.sid.type not in uniq_types:
                    uniq_types.add(obj.sid.type)
                    
                    type_freq[obj.sid.type] = type_freq.get(obj.sid.type, 0)
                    if not (isinstance(obj, overlay.IPCNode) and obj.owner == p):
                        type_freq[obj.sid.type] += 1

                if isinstance(obj, overlay.IPCNode):
                    obj_types["ipc"].append(obj)

                elif isinstance(obj, overlay.FileNode):
                    obj_types["file"].append(obj)

            intermediate_results[name] = [uniq_types, len(result), obj_types["ipc"],
                    obj_types["file"]]

        for node_name, res in intermediate_results.items():
            uniq_types = res[0]
            n_uniq_type = len(uniq_types)
            n_obj = res[1]
            n_ipc = len(res[2])
            n_file = len(res[3])
            type_strength = sum(1 / type_freq[t] for t in uniq_types if type_freq[t] != 0)

            results[node_name] = [n_uniq_type, n_obj, n_ipc, n_file, type_strength]
        
        results = sorted(list(results.items()), key=lambda x: (x[1][sort_by], x[1][1]), reverse=True)
        return results