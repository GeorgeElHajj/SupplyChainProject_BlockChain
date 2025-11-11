"""
Admin API for User Management and Key Generation
Runs on port 5500
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from crypto_utils import CryptoManager
import sqlite3
import datetime
import os
import shutil

app = Flask(__name__)
CORS(app)

# Initialize crypto manager
crypto_manager = CryptoManager(keys_dir="keys")

DB_FILE = "admin.db"


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with tables"""
    conn = get_db()

    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            actor_name TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL,
            active BOOLEAN DEFAULT 1
        )
    ''')

    # Activity log table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create default admin if doesn't exist
    try:
        conn.execute('''
            INSERT INTO users (username, actor_name, role, email, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'Admin', 'admin', 'admin@supply.com',
              datetime.datetime.utcnow().isoformat(), 1))
        conn.commit()
        print("✅ Default admin user created")
    except sqlite3.IntegrityError:
        print("ℹ️  Admin user already exists")

    conn.close()
    print("✅ Database initialized")


def log_activity(user_id, action, details=""):
    """Log user activity"""
    conn = get_db()
    conn.execute('''
        INSERT INTO activity_log (user_id, action, timestamp, details)
        VALUES (?, ?, ?, ?)
    ''', (user_id, action, datetime.datetime.utcnow().isoformat(), details))
    conn.commit()
    conn.close()


def distribute_keys_to_apis(actor_name):
    """
    Copy generated keys to all API directories
    """
    # Define API directories - CORRECTED PATHS
    api_directories = [
        '../SupplierAPI/SupplierAPI/keys',
        '../DistributorAPI/DistributorAPI/keys',
        '../RetailerAPI/RetailerAPI/keys'
    ]

    # Source files in main keys directory
    public_key_source = f'./keys/{actor_name}_public.pem'
    private_key_source = f'./keys/{actor_name}_private.pem'

    # Check if source files exist
    if not os.path.exists(public_key_source) or not os.path.exists(private_key_source):
        return {
            'success': False,
            'error': 'Source key files not found',
            'locations': []
        }

    results = []

    for api_dir in api_directories:
        try:
            # Create directory if it doesn't exist
            if not os.path.exists(api_dir):
                os.makedirs(api_dir)
                print(f"✅ Created directory: {api_dir}")

            # Copy public key
            public_key_dest = os.path.join(api_dir, f'{actor_name}_public.pem')
            shutil.copy2(public_key_source, public_key_dest)

            # Copy private key
            private_key_dest = os.path.join(api_dir, f'{actor_name}_private.pem')
            shutil.copy2(private_key_source, private_key_dest)

            # Set permissions on private key (Unix-like systems)
            try:
                os.chmod(private_key_dest, 0o600)
            except:
                pass  # Windows doesn't support chmod

            results.append({
                'directory': api_dir,
                'success': True
            })

            print(f"✅ Keys copied to: {api_dir}")

        except Exception as e:
            results.append({
                'directory': api_dir,
                'success': False,
                'error': str(e)
            })
            print(f"❌ Failed to copy keys to {api_dir}: {str(e)}")

    return {
        'success': all(r['success'] for r in results),
        'locations': results
    }


# ==================== ENDPOINTS ====================

@app.route('/admin/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'admin-api',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })


@app.route('/admin/users', methods=['GET'])
def list_users():
    """Get all active users"""
    conn = get_db()
    users = conn.execute('''
        SELECT id, username, actor_name, role, email, created_at, active
        FROM users 
        WHERE active = 1
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()

    return jsonify({
        'users': [dict(user) for user in users],
        'count': len(users)
    })


@app.route('/admin/users', methods=['POST'])
def create_user():
    """Create a new user with crypto keys and distribute them to all APIs"""
    data = request.json

    # Validate required fields
    required_fields = ['username', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400

    username = data['username'].strip()
    role = data['role'].lower()
    email = data.get('email', '').strip()

    # Validate role
    valid_roles = ['supplier', 'distributor', 'retailer', 'admin']
    if role not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of: {valid_roles}'}), 400

    # Generate actor name based on role and username
    actor_name = f"{role.title()}_{username}"

    try:
        # Check if username or actor already exists
        conn = get_db()
        existing = conn.execute('''
            SELECT id FROM users WHERE username = ? OR actor_name = ?
        ''', (username, actor_name)).fetchone()

        if existing:
            conn.close()
            return jsonify({'error': 'Username or actor name already exists'}), 400

        # Generate cryptographic keys
        print(f"🔐 Generating keys for {actor_name}...")
        key_result = crypto_manager.register_actor(actor_name)

        if not key_result.get('registered'):
            conn.close()
            return jsonify({'error': 'Failed to generate crypto keys'}), 500

        # Copy keys to all API directories
        print(f"📁 Distributing keys to API directories...")
        distribution_result = distribute_keys_to_apis(actor_name)

        # Save user to database
        cursor = conn.execute('''
            INSERT INTO users (username, actor_name, role, email, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            username,
            actor_name,
            role,
            email,
            datetime.datetime.utcnow().isoformat(),
            1
        ))

        user_id = cursor.lastrowid
        conn.commit()

        # Log activity
        log_activity(user_id, 'user_created', f'Created user {username} with role {role}')

        conn.close()

        print(f"✅ User {username} created successfully")

        return jsonify({
            'success': True,
            'message': 'User created successfully with crypto keys distributed to all APIs',
            'user': {
                'id': user_id,
                'username': username,
                'actor_name': actor_name,
                'role': role,
                'email': email
            },
            'keys': {
                'public_key_path': f"keys/{actor_name}_public.pem",
                'private_key_path': f"keys/{actor_name}_private.pem"
            },
            'distribution': distribution_result
        }), 201

    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@app.route('/admin/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user information"""
    data = request.json

    conn = get_db()

    # Check if user exists
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    # Update fields
    email = data.get('email', user['email'])
    active = data.get('active', user['active'])

    conn.execute('''
        UPDATE users 
        SET email = ?, active = ?
        WHERE id = ?
    ''', (email, active, user_id))
    conn.commit()

    # Log activity
    log_activity(user_id, 'user_updated', f'Updated user {user["username"]}')

    conn.close()

    return jsonify({
        'success': True,
        'message': 'User updated successfully'
    })


@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Deactivate a user (soft delete)"""
    conn = get_db()

    # Check if user exists
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    # Don't allow deleting admin
    if user['role'] == 'admin':
        conn.close()
        return jsonify({'error': 'Cannot delete admin user'}), 403

    # Soft delete (deactivate)
    conn.execute('UPDATE users SET active = 0 WHERE id = ?', (user_id,))
    conn.commit()

    # Log activity
    log_activity(user_id, 'user_deleted', f'Deactivated user {user["username"]}')

    conn.close()

    print(f"✅ User {user['username']} deactivated")

    return jsonify({
        'success': True,
        'message': 'User deactivated successfully'
    })


@app.route('/admin/actors', methods=['GET'])
def list_actors():
    """List all actors with crypto keys"""
    # Get actors with keys from file system
    actors_with_keys = crypto_manager.list_actors()

    # Get user info from database
    conn = get_db()
    users = conn.execute('''
        SELECT actor_name, username, role, email, created_at, active
        FROM users 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()

    # Create lookup dictionary
    user_dict = {user['actor_name']: dict(user) for user in users}

    # Combine information
    result = []
    for actor_name in actors_with_keys:
        user_info = user_dict.get(actor_name, {})
        result.append({
            'actor_name': actor_name,
            'username': user_info.get('username', 'Unknown'),
            'role': user_info.get('role', 'unknown'),
            'email': user_info.get('email', ''),
            'has_keys': True,
            'active': user_info.get('active', False),
            'created_at': user_info.get('created_at', '')
        })

    return jsonify({
        'actors': result,
        'count': len(result)
    })


@app.route('/admin/actors/by-role/<role>', methods=['GET'])
def list_actors_by_role(role):
    """Get all actors filtered by role"""
    conn = get_db()
    users = conn.execute('''
        SELECT actor_name, username, email, created_at
        FROM users 
        WHERE role = ? AND active = 1
        ORDER BY created_at DESC
    ''', (role.lower(),)).fetchall()
    conn.close()

    return jsonify({
        'role': role,
        'actors': [dict(user) for user in users],
        'count': len(users)
    })


@app.route('/admin/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    conn = get_db()

    stats = {}

    # Count by role
    stats['total_users'] = conn.execute('SELECT COUNT(*) FROM users WHERE active = 1').fetchone()[0]
    stats['suppliers'] = conn.execute('SELECT COUNT(*) FROM users WHERE role = "supplier" AND active = 1').fetchone()[0]
    stats['distributors'] = conn.execute('SELECT COUNT(*) FROM users WHERE role = "distributor" AND active = 1').fetchone()[0]
    stats['retailers'] = conn.execute('SELECT COUNT(*) FROM users WHERE role = "retailer" AND active = 1').fetchone()[0]

    # Recent activity
    recent_activity = conn.execute('''
        SELECT u.username, a.action, a.timestamp, a.details
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT 10
    ''').fetchall()

    stats['recent_activity'] = [dict(activity) for activity in recent_activity]

    conn.close()

    return jsonify(stats)


@app.route('/admin/activity', methods=['GET'])
def get_activity_log():
    """Get full activity log"""
    limit = request.args.get('limit', 50, type=int)

    conn = get_db()
    activities = conn.execute('''
        SELECT u.username, u.actor_name, a.action, a.timestamp, a.details
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()

    return jsonify({
        'activities': [dict(activity) for activity in activities],
        'count': len(activities)
    })


@app.route('/admin/keys/redistribute', methods=['POST'])
def redistribute_all_keys():
    """
    Redistribute all existing keys to API directories
    Useful for initial setup or after adding new APIs
    """
    try:
        # Get all actors with keys
        actors = crypto_manager.list_actors()

        if not actors:
            return jsonify({
                'success': False,
                'message': 'No actors found with keys',
                'results': []
            }), 404

        results = []
        for actor_name in actors:
            distribution_result = distribute_keys_to_apis(actor_name)
            results.append({
                'actor': actor_name,
                'result': distribution_result
            })

        success_count = sum(1 for r in results if r['result']['success'])

        return jsonify({
            'success': True,
            'message': f'Redistributed keys for {success_count}/{len(actors)} actors',
            'total_actors': len(actors),
            'successful': success_count,
            'results': results
        })

    except Exception as e:
        print(f"❌ Error redistributing keys: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔐 ADMIN API STARTING")
    print("="*60)

    # Initialize database
    init_db()

    # Ensure all keys directories exist - CORRECTED PATHS
    key_directories = [
        'keys',
        '../SupplierAPI/SupplierAPI/keys',
        '../DistributorAPI/DistributorAPI/keys',
        '../RetailerAPI/RetailerAPI/keys'
    ]

    for directory in key_directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")

    print(f"\n📂 Keys Directories:")
    for directory in key_directories:
        print(f"   - {os.path.abspath(directory)}")

    print(f"\n💾 Database: {os.path.abspath(DB_FILE)}")
    print(f"🌐 Server: http://localhost:5500")
    print("\n📋 Available Endpoints:")
    print("   GET  /admin/health")
    print("   GET  /admin/users")
    print("   POST /admin/users")
    print("   PUT  /admin/users/<id>")
    print("   DELETE /admin/users/<id>")
    print("   GET  /admin/actors")
    print("   GET  /admin/actors/by-role/<role>")
    print("   GET  /admin/stats")
    print("   GET  /admin/activity")
    print("   POST /admin/keys/redistribute")
    print("="*60 + "\n")

    # Run Flask app
    app.run(host='0.0.0.0', port=5500, debug=True)