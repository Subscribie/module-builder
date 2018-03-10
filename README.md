# Subscription Website Builder

- You have a subscription service to sell!
- Each of your packages have unique selling points (USPs)
- Each have a different reoccurring price

Use Karma Subscription Website Builder to build your 
subscription model business & test your market!

# Why 

- Low risk (not very expensive)
- No coding required 
- Simple: Just give us your USPs for each service & price
- Upload your pictures
- Choose between Stripe & Gocardless (more coming soon!)

# Installation 

## 1. Get the code
    git clone git@gitlab.com:karmacrew/subscription-website-builder.git
    cd subscription-website-builder
    git submodule update --init --recursive
    
## 2. Configure 

Set your database credentials for Penguin (Drupal database):
    
    nano Indigo/Penguin/.env.example # the install will copy this over for you to .env 

## 3. Run install.sh

    ./Indigo/install.sh
    
If you make a mistake with your db credentials, Penguin install will fail. Don't worry, it's safe to re-run after setting your database credentials just edit: `nano Indigo/Penguin/.env`

# Running locally
After installing simply run: 

    sudo ./serve.sh