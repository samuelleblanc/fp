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
ver_path = convert_path('./version.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

setup(
    name="movinglines",
    version=main_ns['__version__'].strip('v')+'.5',  # noqa
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
    packages=find_packages('..',exclude=['tests*', 'tutorials*','flight_planning*']),
    namespace_packages=[],
    include_package_data=True,
    zip_safe=True,
    install_requires=['numpy','geopy','scipy','pyephem','Pillow','cartopy','pykml','rasterio','gpxpy','bs4','xlwings','json_tricks','simplekml'],
    #packages=find_namespace_packages(where=""),
    package_dir={"":convert_path('..'),".": ".","map_icons":convert_path("map_icons"),"flt_module":convert_path("flt_module"),"mpl_data":convert_path("mpl-data")},
    package_data={"": ["*.txt","*.tle","*.md","*.json","*.ico","*.tif",
                       os.path.join("map_icons","*.png"),os.path.join("map_icons","*.txt"),
                       os.path.join("flt_module","*.png"),os.path.join("flt_module","*.PNG"),os.path.join("flt_module","*.flt"),
                       os.path.join("mpl-data","*.svg"),os.path.join("mpl-data","*.ppm"),os.path.join("mpl-data","*.xpm"),os.path.join("mpl-data","*.gif"),
                       os.path.join("mpl-data","*.png"),os.path.join("mpl-data","*.gz")],
        ".": ["*.txt","*.tle","*.md","*.json","*.ico","*.tif"],
        "map_icons": ["*.png","*.txt"],
        "flt_modules": ["*.png","*.PNG","*.flt"],
        "mpl_data":["*.svg","*.ppm","*.xpm","*.gif","*.png","*.gz"]
    },
    entry_points=dict(
        console_scripts=['ml = movinglines:main'],
    ),
)