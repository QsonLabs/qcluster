import setuptools
import re
import os


def get_version():
    """Enables single source versioning by considering base project __init__.py authoritative source"""
    semver_re = re.compile(r"""^__version__[\s=]+["'](\d+\.\d+\.\d+)["'\s]+$""")
    init_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "qcluster/__init__.py")
    with open(init_path, "r") as f:
        for line in f:
            match = semver_re.match(line)
            if match:
                return match.group(1)
    raise ValueError("Problem determining version from qcluster init file: %s" % (init_path))


def get_readme_md_contents():
    with open('README.md', 'r') as f:
        desc = f.read()
        return desc


setuptools.setup(
    name="QCluster",
    version=get_version(),
    author="Aaron Rohrbaugh + (See GitHub)",
    author_email="chriso@qsonlabs.com",
    maintainer="Chris O'Connor",
    maintainer_email="chriso@qsonlabs.com",
    description="An SDK to enable quick clustering of microservices.",
    license="Apache License 2.0",
    long_description=get_readme_md_contents(),
    long_description_content_type="text/markdown",
    url="https://github.com/QsonLabs/qcluster",
    packages=setuptools.find_packages(),
    test_suite="tests",
    tests_require=[
        "flake8",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "tox"
    ],
    install_requires=[
        "aiohttp"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Flake8",
        "Framework :: Pytest",
        "Framework :: tox",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Clustering",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires='>=3.8',
)
