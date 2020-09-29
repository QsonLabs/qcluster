import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="QCluster",
    version="0.0.1",
    author="Aaron Rohrbaugh, Katie Pikturna",
    author_email="aaronr@vt.edu, pkat22@vt.edu",
    description="An SDK to enable quick clustering of microservices.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/....",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Apache-2.0",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
