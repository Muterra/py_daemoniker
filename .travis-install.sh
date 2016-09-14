#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then

    git clone https://github.com/MacPython/terryfy
    source terryfy/travis_tools.sh
    get_python_environment  macpython 3.5.2
    
else
    # Install some custom requirements on Linux
fi