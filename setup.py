from setuptools import setup
from Cython.Build import cythonize
from datetime import datetime

setup(
    name="xinput_calibrator",
    version="0." + datetime.now().strftime('%Y%m%d'),
    author_email="sa@eri.su",
    ext_modules = cythonize("xinput_calibrator/xinput_calibrator.py", language_level=3),
    install_requires=[
      ],
    scripts = [],
    data_files=[
        ("xinput_calibrator", [
            "xinput_calibrator/xinput_calibrator.service"
            ])
        ],

    python_requires='>=3.6',
    entry_points={
    'console_scripts': ['xinput_calibrator = xinput_calibrator.xinput_calibratorserver:entry_point'],}
)
