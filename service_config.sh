import sys

config_line = sys.argv[2]

f = open(sys.argv[1], "r+w")
for line in f.readlines():
    line = line.strip()
    if line == config_line:
        sys.exit(0)
    
f.write('%s\n' %config_line)
f.close()

