import os

path = '../_posts/'
old_url = 'https://suyan.peng-ming.cn'
new_url = 'http://suyan.yezy.tech'

path_list = os.listdir(path)
for file_name in path_list:
    if '.md' in file_name:
        with open(path + file_name, 'r') as f:
            lines = f.readlines()

            for i, line in enumerate(lines):
                lines[i] = line.replace(old_url, new_url)

            fl = open(path + file_name, 'w')
            for line in lines:
                fl.write(line)
            fl.close()