import os
import shlex
import subprocess
import pickle
import argparse

from config import *

parser = argparse.ArgumentParser(description="Process an Android firmware image and save all object names to file")

parser.add_argument("image_name", help="path of extracted firmware image")
parser.add_argument("--vendor", default="aosp", help="")

args = parser.parse_args()
image_name = args.image_name

# Input name of extracted firmware image you want
# a = input("Image Name: ")
#a = "shamu-nbd91x-factory-f653ffea"

# Automates the saving and the debugging stage
vendor = args.vendor
command = ""
if not vendor:
    if os.path.exists('policy/aosp/'+image_name):
        os.system('./process.py --vendor aosp policy/aosp/' + image_name + ' --save')
        command = "./process.py --vendor aosp policy/aosp/" + image_name + " --load --debug"
        vendor = 'aosp'

    elif os.path.exists('policy/samsung/'+image_name):
        os.system('./process.py --vendor samsung policy/samsung/' + image_name + ' --save')
        command = "./process.py --vendor samsung policy/samsung/" + image_name + " --load --debug"
        vendor = 'samsung'

else:
    vendor = vendor.lower()
    policy_path = 'policy/%s/%s' % (vendor, image_name)
    if os.path.exists(policy_path):
        os.system('./process.py --vendor %s %s --save' % (vendor, policy_path))
        command = "./process.py --vendor %s %s --load --debug" % (vendor, policy_path)

if not command:
    print("Could not find image %s" % image_name)

args = shlex.split(command)
p = subprocess.Popen(args, stdin=subprocess.PIPE)

tmp_pickle_file = "autoOutput.txt"

pickling_code = 'import pickle; f=open("%s", "wb"); pickle.dump(inst, f); f.close()' % tmp_pickle_file

p.communicate(input=pickling_code.encode('utf-8'))

f = open(tmp_pickle_file, 'rb')
try:
    inst = pickle.load(f)
finally:
    f.close()
    os.system('rm %s' % tmp_pickle_file)

try:
    os.mkdir('zresults')
except OSError as error:
    pass

# Saves all the variables from the object into the zresults folder with the name of the image
b = "zresults/"+image_name+"_output.txt" 

def write_object_list(fd, object_type, object_list):
    for o in object_list: fd.write("%s : %s\n" % (object_type, str(o)))

with open(b, 'w') as w:

    write_object_list(w, "FILE_CONTEXT", inst.file_contexts)
    write_object_list(w, "OBJECT", inst.objects.keys())
    write_object_list(w, "PROCESS", inst.processes.keys())
    write_object_list(w, "SUBJECT", inst.subjects.keys())
    write_object_list(w, "DOMAIN_ATTRIBUTE", inst.domain_attributes)
    write_object_list(w, "SEPOLICY_CLASS", inst.sepolicy["classes"].keys())

# Cleaning up
# w.close()


print(image_name + '_output.txt has been generated and saved into zresults')

# Pop up the menu to search through the fruit of our labor
# search = True

# #Open it up in tmux
# def tmux(command):
#     os.system('tmux %s' % command)

# def tmux_shell(command):
#     tmux('send-keys "%s" "C-m"' % command)

# tmux('new-session -d -s analysis')
# tmux('split-window -h')
# tmux('select-pane -t 1')
# tmux_shell('./process.py --vendor ' + vendor + ' policy/' + vendor + '/' + a + ' --load --prolog')
# tmux('select-pane -t 0')
# tmux_shell('python3 autoSearch.py ' + b)
# tmux('attach')
