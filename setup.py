from setuptools import setup, find_packages

setup(
    name="gmail_processor",
    version="0.1",
    description="Process Gmail inbox emails using custom rules",
    packages=find_packages(),
    install_requires=[
        "google-auth-oauthlib==1.2.0",
        "google-api-python-client==2.121.0",
        "pytest==8.1.1",
        "tqdm==4.67.1",
    ],
    python_requires=">=3.12",
)
