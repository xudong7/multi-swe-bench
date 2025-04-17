from setuptools import find_packages, setup

setup(
    name="multi-swe-bench",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "dataclasses_json",
        "docker",
        "tqdm",
        "gitpython",
        "toml",
        "pyyaml",
        "PyGithub",
        "unidiff",
    ],
    author="Daoguang Zan",
    author_email="zandaoguang@bytedance.com",
    description="Multi-SWE-bench: A Multilingual Benchmark for Issue Resolving",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/multi-swe-bench/multi-swe-bench",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
