#import libraries.
import sys,os
#set the correct path. pong needs both access to Graphics and Controllers.
cwd = os.getcwd()
sys.path.append(cwd)
sys.path.append(cwd+"/patterns/Graphics/")
sys.path.append(cwd+"/patterns/Controllers/")
#this allows a nice import.
#like: from Pong import *
from Pong import *
