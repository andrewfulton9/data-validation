# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Package Setup script for TensorFlow Data Validation."""

import os
import platform
import shutil
import subprocess
import sys

# pylint:disable=g-bad-import-order
# setuptools must be imported prior to distutils.
from distutils.command import build
from pathlib import Path

import setuptools
from setuptools import find_packages, setup
from setuptools.command.install import install
from setuptools.dist import Distribution

# pylint:enable=g-bad-import-order


class _BuildCommand(build.build):
    """Build everything that is needed to install.

    This overrides the original distutils "build" command to to run bazel_build
    command before any sub_commands.

    build command is also invoked from bdist_wheel and install command, therefore
    this implementation covers the following commands:
      - pip install . (which invokes bdist_wheel)
      - python setup.py install (which invokes install command)
      - python setup.py bdist_wheel (which invokes bdist_wheel command)
    """

    def _build_cc_extensions(self):
        return True

    # Add "bazel_build" command as the first sub_command of "build". Each
    # sub_command of "build" (e.g. "build_py", "build_ext", etc.) is executed
    # sequentially when running a "build" command, if the second item in the tuple
    # (predicate method) is evaluated to true.
    sub_commands = [
        ("bazel_build", _build_cc_extensions),
    ] + build.build.sub_commands


class _BazelBuildCommand(setuptools.Command):
    """Build TFDV C++ extensions and public protos with Bazel.

    Running this command will populate foo_pb2.py file next to your foo.proto
    file.
    """

    def initialize_options(self):
        pass

    def finalize_options(self):
        self._bazel_cmd = shutil.which("bazel")
        if not self._bazel_cmd:
            raise RuntimeError(
                'Could not find "bazel" binary. Please visit '
                "https://docs.bazel.build/versions/master/install.html for "
                "installation instruction."
            )
        self._additional_build_options = []
        if platform.system() == "Darwin":
            self._additional_build_options = ["--macos_minimum_os=10.14"]

    def run(self):
        subprocess.check_call(
            [self._bazel_cmd, "run", "-c", "opt"]
            + self._additional_build_options
            + ["//tensorflow_data_validation:move_generated_files"],
            # Bazel should be invoked in a directory containing bazel WORKSPACE
            # file, which is the root directory.
            cwd=os.path.dirname(os.path.realpath(__file__)),
            env=dict(os.environ, PYTHON_BIN_PATH=sys.executable),
        )


# TFDV is not a purelib. However because of the extension module is not built
# by setuptools, it will be incorrectly treated as a purelib. The following
# works around that bug.
class _InstallPlatlibCommand(install):
    def finalize_options(self):
        install.finalize_options(self)
        self.install_lib = self.install_platlib


class _BinaryDistribution(Distribution):
    """This class is needed in order to create OS specific wheels."""

    def is_pure(self):
        return False

    def has_ext_modules(self):
        return True


def _make_mutual_information_requirements():
    return ["scikit-learn>=1.0,<2", "scipy>=1.5,<2"]


def _make_visualization_requirements():
    return [
        "ipython>=7,<8",
    ]


def _make_docs_requirements():
    return [
        req
        for req in Path("./requirements-docs.txt")
        .expanduser()
        .resolve()
        .read_text()
        .splitlines()
        if req
    ]


def _make_all_extra_requirements():
    return (
        *_make_mutual_information_requirements(),
        *_make_visualization_requirements(),
        *_make_docs_requirements(),
    )


def select_constraint(default, nightly=None, git_master=None):
    """Select dependency constraint based on TFX_DEPENDENCY_SELECTOR env var."""
    selector = os.environ.get("TFX_DEPENDENCY_SELECTOR")
    if selector == "UNCONSTRAINED":
        return ""
    elif selector == "NIGHTLY" and nightly is not None:
        return nightly
    elif selector == "GIT_MASTER" and git_master is not None:
        return git_master
    else:
        return default


# Get version from version module.
with open("tensorflow_data_validation/version.py") as fp:
    globals_dict = {}
    exec(fp.read(), globals_dict)  # pylint: disable=exec-used
__version__ = globals_dict["__version__"]

# Get the long description from the README file.
with open("README.md") as fp:
    _LONG_DESCRIPTION = fp.read()

setup(
    name="tensorflow-data-validation",
    version=__version__,
    author="Google LLC",
    author_email="tensorflow-extended-dev@googlegroups.com",
    license="Apache 2.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    namespace_packages=[],
    # Make sure to sync the versions of common dependencies (absl-py, numpy,
    # six, and protobuf) with TF.
    install_requires=[
        "absl-py>=0.9,<2.0.0",
        'apache-beam[gcp]>=2.53,<3;python_version>="3.11"',
        'apache-beam[gcp]>=2.50,<2.51;python_version<"3.11"',
        # TODO(b/139941423): Consider using multi-processing provided by
        # Beam's DirectRunner.
        "joblib>=1.2.0",  # Dependency for multi-processing.
        "numpy>=1.22.0",
        "pandas>=1.0,<2",
        'protobuf>=4.25.2,<6.0.0;python_version>="3.11"',
        'protobuf>=4.21.6,<6.0.0;python_version<"3.11"',
        "pyarrow>=10,<11",
        "pyfarmhash>=0.2.2,<0.4",
        "six>=1.12,<2",
        "tensorflow>=2.17,<2.18",
        "tensorflow-metadata"
        + select_constraint(
            default=">=1.17.1,<1.18",
            nightly=">=1.18.0.dev",
            git_master="@git+https://github.com/tensorflow/metadata@master",
        ),
        "tfx-bsl"
        + select_constraint(
            default=">=1.17.1,<1.18",
            nightly=">=1.18.0.dev",
            git_master="@git+https://github.com/tensorflow/tfx-bsl@master",
        ),
    ],
    extras_require={
        "mutual-information": _make_mutual_information_requirements(),
        "visualization": _make_visualization_requirements(),
        "dev": ["precommit"],
        "docs": _make_docs_requirements(),
        "test": [
            "pytest",
            "scikit-learn",
            "scipy",
        ],
        "all": _make_all_extra_requirements(),
    },
    python_requires=">=3.9,<4",
    packages=find_packages(),
    include_package_data=True,
    package_data={"": ["*.lib", "*.pyd", "*.so"]},
    zip_safe=False,
    distclass=_BinaryDistribution,
    description="A library for exploring and validating machine learning data.",
    long_description=_LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    keywords="tensorflow data validation tfx",
    url="https://www.tensorflow.org/tfx/data_validation/get_started",
    download_url="https://github.com/tensorflow/data-validation/tags",
    requires=[],
    cmdclass={
        "install": _InstallPlatlibCommand,
        "build": _BuildCommand,
        "bazel_build": _BazelBuildCommand,
    },
)
