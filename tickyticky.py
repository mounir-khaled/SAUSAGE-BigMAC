import itertools

# Open resulting file from the command ran in the previous 
# step which should be out.txt
f = open('out.txt', 'r')
counter = 0
marker = 0
bindCount = 0
bc = 0
bc1 = 0
myList = []

# For each line in the out file, look for the delimiter and 
# take note of the range from one delimiter to the other 
# that has the word Binder in it.
for line in f:
    counter = counter + 1
    if "--------" in line:
        if bindCount > 0:
            #print("(" + str(marker) + ", " + str(counter) + ")")
            myList.append([marker, counter])
            bindCount = 0
            bc = bc + 1
        marker = counter
    if "Binder" in line:
        bindCount = bindCount + 1
        bc1 = bc1 + 1

# This prints our list of ranges that we will then use to get
# the methods we want with Binder in them     
print(myList)

f.seek(0)
counter = 0
p = False

for rnge in myList:
    for line in f:
        if counter == rnge[0]:
            p = True

        if counter == rnge[1]:
            p = False

        if p:
            # Add lines for the output write here. Just left at print
            # due to debugging reasons
            print(line)
        
        counter = counter + 1

    counter = 0
    f.seek(0)