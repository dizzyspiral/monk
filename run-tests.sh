if [ $# -eq 0 ]; then
    python3 -m unittest discover -t ./ -s test/unittest
else
    python3 -m unittest $1
fi
