from setuptools import setup, find_packages

setup(
    name='refactoring_tool',
    version='0.1.0',
    author='James Olaitan',
    author_email='olaitan@uni.minerva.edu',
    description='An automated refactoring tool with machine learning error filtering.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/JamesOlaitan/Automated-Refactoring-Tool-with-ML-Error-Filtering',
    packages=find_packages(),
    install_requires=[
        'astor>=0.8.1',          # For AST manipulation and code generation
        'scikit-learn>=0.24.2',  # For ML algorithms
        'pandas>=1.2.4',         # For data handling
        'numpy>=1.20.3',         # For numerical computations
        'pytest>=6.2.4',         # For testing
        'click>=7.1.2',          # For CLI
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'refactor=refactoring_tool.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Code Generators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    keywords='refactoring code-analysis machine-learning',
    license='MIT',
    include_package_data=True,
    zip_safe=False,
)