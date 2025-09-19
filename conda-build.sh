#/bin/bash
VERSION='1.56'

conda activate ml
#conda build .
#conda convert --platform all /home/sam/mambaforge/conda-bld/linux-64/movinglines-$VERSION-py39_1000.tar.bz2 -o conda-out/
#conda convert --platform all /home/sam/mambaforge/conda-bld/linux-64/movinglines-$VERSION-py38_1000.tar.bz2 -o conda-out/

#cp /home/sam/mambaforge/conda-bld/linux-64/movinglines-$VERSION-py38_1000.tar.bz2 conda-out/linux-64/
#cp /home/sam/mambaforge/conda-bld/linux-64/movinglines-$VERSION-py39_1000.tar.bz2 conda-out/linux-64/

#conda convert --platform all conda-out/win-64/movinglines-$VERSION-py39_1000.tar.bz2 -o conda-out/
#conda convert --platform all conda-out/win-64/movinglines-$VERSION-py38_1000.tar.bz2 -o conda-out/

anaconda upload ./conda-out/osx*/movinglines-$VERSION-py3?_1000.tar.bz2
anaconda upload ./conda-out/win*/movinglines-$VERSION-py3?_1000.tar.bz2
anaconda upload ./conda-out/linux-??/movinglines-$VERSION-py3?_1000.tar.bz2
