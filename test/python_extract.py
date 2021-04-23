# -*- coding: utf-8 -*-
with open('padron_reducido.txt', 'r') as file:
    content = file.readlines()
for line in content:
    print("line", line)
