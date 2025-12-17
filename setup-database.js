// setup-database.js
const { MongoClient } = require('mongodb');

async function setupDatabase() {
    const uri = 'mongodb://localhost:27017';
    const client = new MongoClient(uri);

    try {
        console.log('🔌 Connecting to MongoDB...');
        await client.connect();
        const database = client.db('water_billing_db');

        // ========== CREATE COLLECTIONS ==========
        console.log('📁 Creating collections...');

        const collections = [
            'customers',
            'invoices',
            'meter_readings',
            'payments',
            'rate_config',
            'customer_auth',
            'usage_alerts',
            'rate_change_audit',
            'notifications'
        ];

        for (const collectionName of collections) {
            try {
                await database.createCollection(collectionName);
                console.log(`✅ Created: ${collectionName}`);
            } catch (error) {
                console.log(`ℹ️  Collection ${collectionName} already exists`);
            }
        }

        // ========== INSERT CUSTOMERS ==========
        console.log('\n👥 Inserting customers...');

        const customersData = [
            { account_number: "3", name: "SOUTH LAKE DAIRY", customer_type: "COMMERCIAL" },
            { account_number: "4", name: "JOSALI MOZIT", customer_type: "RESIDENTIAL" },
            { account_number: "5", name: "JOSALI (B)", customer_type: "RESIDENTIAL" },
            { account_number: "6", name: "LUCY KIRAGU", customer_type: "RESIDENTIAL" },
            { account_number: "7", name: "MOSES WANNAINA", customer_type: "RESIDENTIAL" },
            { account_number: "8", name: "KARANJA 401", customer_type: "COMMERCIAL" },
            { account_number: "9", name: "HELLEN GUANTAI", customer_type: "RESIDENTIAL" },
            { account_number: "10", name: "MARY WATHEBA", customer_type: "RESIDENTIAL" },
            { account_number: "11", name: "NANCY WANJIRU", customer_type: "RESIDENTIAL" },
            { account_number: "12", name: "ESTHER MUTHONI", customer_type: "RESIDENTIAL" },
            { account_number: "13", name: "DAVID THEURI", customer_type: "RESIDENTIAL" },
            { account_number: "14", name: "PAUL NUGU", customer_type: "RESIDENTIAL" },
            { account_number: "15", name: "EMMA WAMBU", customer_type: "RESIDENTIAL" },
            { account_number: "16", name: "ROBERT KIMENIU (HOME)", customer_type: "RESIDENTIAL" },
            { account_number: "17", name: "ROBERT KIMENIU (PLOT)", customer_type: "RESIDENTIAL" },
            { account_number: "18", name: "LEAH WANJIKU", customer_type: "RESIDENTIAL" },
            { account_number: "19", name: "PRISCILLAH NIERI", customer_type: "RESIDENTIAL" },
            { account_number: "20", name: "GEOFREY NZEI", customer_type: "RESIDENTIAL" },
            { account_number: "21", name: "PAUL MWANGI (HOME)", customer_type: "RESIDENTIAL" },
            { account_number: "22", name: "PAUL MWANGI (PLOT)", customer_type: "RESIDENTIAL" },
            { account_number: "23", name: "HARON MACHARIA", customer_type: "RESIDENTIAL" },
            { account_number: "24", name: "JOYCE EDWIN", customer_type: "RESIDENTIAL" },
            { account_number: "25", name: "PATRICK KARANJA", customer_type: "RESIDENTIAL" },
            { account_number: "26", name: "NICHOLAS", customer_type: "RESIDENTIAL" },
            { account_number: "27", name: "JAMES MUCHERU", customer_type: "RESIDENTIAL" },
            { account_number: "28", name: "THOMAS WANANNA", customer_type: "RESIDENTIAL" },
            { account_number: "29", name: "BEATRICE KIGURU", customer_type: "RESIDENTIAL" },
            { account_number: "30", name: "MARTHA NUGUNA", customer_type: "RESIDENTIAL" },
            { account_number: "31", name: "PETER WACHIRA", customer_type: "RESIDENTIAL" },
            { account_number: "32", name: "KEFA AWAKOJ - JOSEPH", customer_type: "RESIDENTIAL" },
            { account_number: "33", name: "ALEX MWAI", customer_type: "RESIDENTIAL" },
            { account_number: "34", name: "WASHINGTON NORANGU", customer_type: "RESIDENTIAL" },
            { account_number: "35", name: "PETER MAINA", customer_type: "RESIDENTIAL" },
            { account_number: "36", name: "HANNAH KIMANI", customer_type: "RESIDENTIAL" },
            { account_number: "37", name: "JAMES KARUKI (HOME)", customer_type: "RESIDENTIAL" },
            { account_number: "38", name: "JAMES KARUKI (PLOT)", customer_type: "RESIDENTIAL" },
            { account_number: "39", name: "MICHAEL THUO", customer_type: "RESIDENTIAL" },
            { account_number: "40", name: "HARRISON GITAU", customer_type: "RESIDENTIAL" },
            { account_number: "41", name: "BETRA CARWASH", customer_type: "COMMERCIAL" },
            { account_number: "42", name: "TWO WAYS BAR", customer_type: "COMMERCIAL" },
            { account_number: "43", name: "HOTEL", customer_type: "COMMERCIAL" },
            { account_number: "44", name: "BUTCHERY", customer_type: "COMMERCIAL" },
            { account_number: "45", name: "JUDITH", customer_type: "RESIDENTIAL" },
            { account_number: "46", name: "PETER NGATIA", customer_type: "RESIDENTIAL" }
        ];

        // Enhance customer data
        const enhancedCustomers = customersData.map((customer, index) => ({
            ...customer,
            phone: `+2547${10000000 + index}`,
            email: `${customer.name.toLowerCase().replace(/[^a-z]/g, '')}@example.com`,
            location: getLocation(index),
            meter_number: `MTR${customer.account_number.padStart(5, '0')}`,
            connection_date: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000),
            status: "ACTIVE",
            balance: 0,
            created_at: new Date(),
            updated_at: new Date()
        }));

        const customersCollection = database.collection('customers');
        const existingCount = await customersCollection.countDocuments();

        if (existingCount === 0) {
            const result = await customersCollection.insertMany(enhancedCustomers);
            console.log(`✅ Inserted ${result.insertedCount} customers`);
        } else {
            console.log(`ℹ️  Customers already exist (${existingCount} records)`);
        }

        // ========== CREATE INDEXES ==========
        console.log('\n📊 Creating indexes...');

        // Customers indexes
        await customersCollection.createIndex({ account_number: 1 }, { unique: true });
        await customersCollection.createIndex({ meter_number: 1 }, { unique: true });
        await customersCollection.createIndex({ customer_type: 1 });
        await customersCollection.createIndex({ status: 1 });
        console.log('✅ Customer indexes created');

        // Invoices indexes
        const invoicesCollection = database.collection('invoices');
        await invoicesCollection.createIndex({ invoice_number: 1 }, { unique: true });
        await invoicesCollection.createIndex({ status: 1 });
        console.log('✅ Invoice indexes created');

        // Meter readings indexes
        const meterReadingsCollection = database.collection('meter_readings');
        await meterReadingsCollection.createIndex({ customer_id: 1, recorded_at: -1 });
        console.log('✅ Meter reading indexes created');

        // ========== INSERT RATE CONFIG ==========
        console.log('\n💰 Inserting rate configuration...');

        const rateCollection = database.collection('rate_config');
        const rateCount = await rateCollection.countDocuments();

        if (rateCount === 0) {
            await rateCollection.insertMany([
                {
                    mode: "FIXED",
                    value: 50.0,
                    description: "Residential rate per cubic meter",
                    customer_type: "RESIDENTIAL",
                    effective_from: new Date("2024-01-01"),
                    effective_to: null,
                    created_at: new Date(),
                    updated_at: new Date()
                },
                {
                    mode: "FIXED",
                    value: 75.0,
                    description: "Commercial rate per cubic meter",
                    customer_type: "COMMERCIAL",
                    effective_from: new Date("2024-01-01"),
                    effective_to: null,
                    created_at: new Date(),
                    updated_at: new Date()
                }
            ]);
            console.log('✅ Rate configurations inserted');
        } else {
            console.log('ℹ️  Rate configurations already exist');
        }

        // ========== VERIFY SETUP ==========
        console.log('\n🔍 Verifying setup...');

        const collectionNames = await database.listCollections().toArray();
        console.log(`\n📁 Collections in database:`);
        collectionNames.forEach(col => console.log(`   • ${col.name}`));

        const totalCustomers = await customersCollection.countDocuments();
        console.log(`\n👥 Total customers: ${totalCustomers}`);

        console.log('\n🎉 Database setup completed successfully!');
        console.log('\n📋 You can now:');
        console.log('   1. View data in MongoDB Compass');
        console.log('   2. Start building your API');
        console.log('   3. Use the data for your water billing system');

    } catch (error) {
        console.error('❌ Error:', error.message);
        console.log('\n💡 Troubleshooting tips:');
        console.log('   1. Make sure MongoDB is running');
        console.log('   2. Open MongoDB Compass and try to connect');
        console.log('   3. Check if port 27017 is free');
    } finally {
        await client.close();
        console.log('\n🔒 MongoDB connection closed');
    }
}

function getLocation(index) {
    const locations = [
        "Nairobi Central",
        "South Lake Estate",
        "Kiambu Road",
        "Thika Road",
        "Westlands",
        "Karen",
        "Langata",
        "Kileleshwa",
        "Lavington",
        "Ruiru",
        "Juja",
        "Githurai",
        "Embakasi",
        "Donholm",
        "Buruburu",
        "Umoja",
        "Kasarani",
        "Roysambu",
        "Kahawa West",
        "Kahawa Sukari",
        "Kikuyu",
        "Limuru",
        "Kiambu Town",
        "Thika Town",
        "Ruiru Town",
        "Juja Town",
        "Githurai 45",
        "Mwiki",
        "Kariobangi",
        "Dandora",
        "Kayole",
        "Njiru",
        "Muthaiga",
        "Mombasa Road",
        "Ngong Road",
        "Waiyaki Way",
        "Tom Mboya Street",
        "Ronald Ngala Street",
        "Moi Avenue"
    ];
    return locations[index % locations.length];
}

// Run the setup
setupDatabase();
