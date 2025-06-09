# Using Neon with Netlify

This project relies on a PostgreSQL database. Neon provides a managed Postgres service that can integrate directly with Netlify.

## Retrieve your connection string
1. Open your **Project Dashboard** in the Neon Console.
2. Click **Connect** to open the *Connect to your database* modal.
3. Select the branch, compute size, database, and role you wish to use.
4. Copy the generated connection string. It looks similar to:
   ```
   postgresql://<user>:<password>@<hostname>/dbname?sslmode=require
   ```
   The hostname includes the compute ID and typically ends with `-pooler.neon.tech` when connection pooling is enabled.

## Local development
1. Create a `.env` file at the project root if one does not exist.
2. Add the connection string:
   ```
   DATABASE_URL=postgresql://<user>:<password>@<hostname>/dbname?sslmode=require
   ```
3. Run your application (or `netlify dev` if testing via Netlify CLI) and it will connect to Neon using this variable.

## Deploying on Netlify
1. Ensure your Netlify project is linked to your repository.
2. Set the `DATABASE_URL` environment variable for the deployed site:
   ```
   netlify env:set DATABASE_URL "postgresql://<user>:<password>@<hostname>/dbname?sslmode=require"
   ```
3. Deploy your site:
   ```
   netlify deploy --prod
   ```
   Netlify will build and deploy your application with the Neon connection string available via `DATABASE_URL`.

## Optional: Netlify DB
Netlify DB is a one-click Postgres service powered by Neon. Running `netlify init db` from your project directory provisions a Neon database and automatically configures the `DATABASE_URL` environment variable in Netlify. You can later claim the database in your Neon account.

