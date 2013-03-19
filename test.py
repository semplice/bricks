import bricks.engine
import sys

#pkg = bricks.engine.Package(sys.argv[1])
#pkg.remove()

bricks.engine.remove(sys.argv[1:])
