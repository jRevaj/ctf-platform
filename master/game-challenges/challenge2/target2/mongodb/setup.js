// MongoDB setup script for CTF challenge
// This script is run during container startup to initialize the database

// Connect to database
// This syntax works in both mongo and mongosh
conn = new Mongo();
db = conn.getDB("ctf_app");

// Drop existing collections to ensure clean setup
db.users.drop();
db.admin_notes.drop();
db.secrets.drop();

// Create users collection and insert sample users
db.users.insertMany([
    {
        username: "admin",
        password: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", // sha256 of "test"
        role: "admin",
        email: "admin@example.com",
        created_at: new Date()
    },
    {
        username: "user",
        password: "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", // sha256 of "password"
        role: "user",
        email: "user@example.com",
        created_at: new Date()
    }
]);

// Create admin_notes collection with sensitive information
db.admin_notes.insertMany([
    {
        title: "Jenkins credentials",
        note: "Jenkins admin user: admin, password: jenkins_password",
        created_at: new Date()
    },
    {
        title: "MySQL backup credentials",
        note: "MySQL backup user: backup, password: backup123",
        created_at: new Date()
    }
]);

// Create secrets collection with the FLAG_PLACEHOLDER_6
// This contains the flag that should be found during the CTF
print("Adding FLAG_PLACEHOLDER_6 to secrets collection...");
db.secrets.insertOne({
    title: "Database Backup Key",
    content: "FLAG_PLACEHOLDER_6",
    created_at: new Date()
});

// Create a MongoDB user with weak credentials (intentional vulnerability)
try {
    db.createUser({
        user: "dbuser",
        pwd: "dbpass",
        roles: [{ role: "readWrite", db: "ctf_app" }]
    });
    print("MongoDB user created successfully");
} catch (e) {
    print("Error creating MongoDB user: " + e);
    // Continue execution even if user creation fails
}

print("MongoDB setup completed successfully"); 