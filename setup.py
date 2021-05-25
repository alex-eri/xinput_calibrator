from setuptools import setup
from Cython.Build import cythonize
from datetime import datetime

setup(
    name="touch_calibrator",
    version="1." + datetime.now().strftime('%Y%m%d'),
    author_email="sa@eri.su",
    ext_modules = cythonize("xinput_calibrator/touch_calibrator.py", language_level=3),
    install_requires=[
        'gi'
      ],
    scripts = [],
    # data_files=[
    #     ("touch_calibrator", [
    #         "touch_calibrator.service"
    #         ])
    #     ],

    python_requires='>=3.5',
    entry_points={
    'console_scripts': ['touch_calibrator = touch_calibrator:entry_point'],}
)
