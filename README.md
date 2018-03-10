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

    git clone git@gitlab.com:karmacrew/subscription-website-builder.git
    cd subscription-website-builder
    git submodule update --init --recursive
    ./Indigo/install.sh
    
Penguin install will fail with incorect db credentials. It's safe to re-run after setting your database credentials in: `nano Indigo/Penguin/.env`
