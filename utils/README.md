# Local Development

## Prereqs
- Install [Anaconda3](https://www.anaconda.com/download/)
- Once installed:
    1. Open the Anaconda Prompt or your terminal.
    2. Type `conda create --name mlmb-utils python=3.11`

## Local Development
1. Open the Anaconda Prompt or your terminal.
3. Activate the environment: `conda activate mlmb-utils`
3. In the terminal, change directories to the current folder (aka the `utils` folder)
4. Install the packages: `pip install -r requirements.txt`

## Updating packages
If you installed new packages or upgraded packages using `pip`, run the following: `pip freeze > requirements.txt`