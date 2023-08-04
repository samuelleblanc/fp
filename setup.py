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

main_ns = {}
ver_path = convert_path('./version.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

setup(
    name="ml",
    version=main_ns['__version__'],  # noqa
    description="Moving Lines - Research flight planner",
    long_description=long_description,
    classifiers="Development Status :: 5 - Production/Stable",
    keywords="ml",
    maintainer="Samuel LeBlanc",
    maintainer_email="samuel.leblanc@nasa.gov",
    author="Samuel LeBlanc",
    author_email="samuel.leblanc@nasa.gov",
    license="GPL-3.0",
    url="https://github.com/samuelleblanc/fp",
    platforms="any",
    packages=find_packages(exclude=['tests*', 'tutorials*']),
    namespace_packages=[],
    include_package_data=True,
    zip_safe=False,
    install_requires=['numpy','geopy','scipy','pyephem','Pillow','cartopy','pykml','rasterio','gpxpy','bs4','xlwings','json_tricks','simplekkml'],
    #packages=find_namespace_packages(where=""),
    package_dir={"": "","map_icons":"map_icons","flt_modules":"flt_modules","mpl_data":"mpl-data"},
    package_data={
        "": ["*.txt","*.tle","*.md","*.json","*.ico","*.tif"],
        "map_icons": ["*.png","*.txt"],
        "flt_modules": ["*.png","*.PNG","*.flt"],
        "mpl_data":["*.svg","*.ppm","*.xpm","*.gif","*.png","*.gz"]
    },
    entry_points=dict(
        console_scripts=['ml = ml:main'],
    ),
)