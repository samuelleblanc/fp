"""

    ml.setup
    ~~~~~~~~~~~~~~~~

    setuptools script

    This file is part of Moving Lines Flight planner.

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

from setuptools import setup, find_packages
long_description = open('README.md').read()
from distutils.util import convert_path
import os

main_ns = {}
ver_path = convert_path('./movinglines/version.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

setup(
    name="movinglines",
    version=main_ns['__version__'].strip('v'),  # noqa
    description="Moving Lines - Research flight planner",
    long_description_content_type = 'text/markdown',
    long_description=long_description,
    classifiers=['Intended Audience :: Science/Research',
                 "Development Status :: 5 - Production/Stable",
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3'],
    keywords="ml",
    maintainer="Samuel LeBlanc",
    maintainer_email="samuel.leblanc@nasa.gov",
    author="Samuel LeBlanc",
    author_email="samuel.leblanc@nasa.gov",
    license="GPL-3.0",
    url="https://github.com/samuelleblanc/fp",
    platforms="any",
    packages=find_packages('.',exclude=['tests*', 'tutorials*','flight_planning*','fp*','py*']),
    namespace_packages=[],
    include_package_data=True,
    zip_safe=False,
    install_requires=['numpy','geopy','scipy','pyephem','Pillow','cartopy<0.20.1','shapely<2.0.0','pykml','rasterio','gpxpy','bs4','xlwings','json_tricks','simplekml','matplotlib<3.6.0','owslib'],
    #packages=find_namespace_packages(where=""),
    package_dir={"":convert_path('.'),".": ".","movinglines.map_icons":convert_path("movinglines/map_icons"),"movinglines.flt_module":convert_path("movinglines/flt_module"),
                 "movinglines.mpl-data":convert_path("movinglines/mpl-data")},
    package_data={"": ["*.txt","*.tle","*.md","*.json","*.ico","*.tif",#]},
                       convert_path(os.path.join("movinglines","*.txt")),convert_path(os.path.join("movinglines","*.tle")),convert_path(os.path.join("movinglines","*.md")),
                       convert_path(os.path.join("movinglines","*.json")),convert_path(os.path.join("movinglines","*.ico")),convert_path(os.path.join("movinglines","*.tif")),
                       convert_path(os.path.join("movinglines","map_icons","*.png")),convert_path(os.path.join("movinglines","map_icons","*.txt")),
                       convert_path(os.path.join("movinglines","flt_module","*.png")),convert_path(os.path.join("movinglines","flt_module","*.PNG")),convert_path(os.path.join("movinglines","flt_module","*.flt")),
                       convert_path(os.path.join("movinglines","mpl-data","*.svg")),convert_path(os.path.join("movinglines","mpl-data","*.ppm")),convert_path(os.path.join("movinglines","mpl-data","*.xpm")),
                       convert_path(os.path.join("movinglines","mpl-data","*.gif")),
                       convert_path(os.path.join("movinglines","mpl-data","*.png")),convert_path(os.path.join("movinglines","mpl-data","*.gz")),
                       convert_path("./movinglines/mpl-data/*"),convert_path("./movinglines/map_icons/*"),convert_path("./movinglines/flt_module/*"),convert_path("./movinglines/hooks/*")],
        ".": ["*.txt","*.tle","*.md","*.json","*.ico","*.tif","movinglines/flt_module/*.flt","movinglines/flt_module/*.png"],
        "movinglines.map_icons": ["*.png","*.txt",os.path.join("movinglines","map_icons","*.png"),os.path.join("movinglines","map_icons","*.txt")],
        "flt_modules": ["*.png","*.PNG","*.flt",os.path.join("movinglines","flt_module","*.png"),os.path.join("movinglines","flt_module","*.PNG"),os.path.join("movinglines","flt_module","*.flt")],
        "movinglines.mpl-data":["*.svg","*.ppm","*.xpm","*.gif","*.png","*.gz",os.path.join("movinglines","mpl-data","*.svg"),os.path.join("movinglines","mpl-data","*.ppm"),os.path.join("movinglines","mpl-data","*.xpm"),
                       os.path.join("movinglines","mpl-data","*.gif"),
                       os.path.join("movinglines","mpl-data","*.png"),os.path.join("movinglines","mpl-data","*.gz")],
        "movinglines.flt_modules":["*.png","*.PNG","*.flt",os.path.join("movinglines","flt_module","*.png"),os.path.join("movinglines","flt_module","*.PNG"),os.path.join("movinglines","flt_module","*.flt")]
    },
    entry_points=dict(
        console_scripts=['ml = movinglines:main'],
    ),
)