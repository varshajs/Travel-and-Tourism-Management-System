from flask import Flask, render_template, request, redirect, url_for, flash,session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from mysql.connector import errorcode

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management and flash messages

# Configure the MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",  # Replace with your MySQL password if necessary
    database="travelmanagement"
)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the username from the form
        username = request.form['username']
        # You can store the username in the session or pass it directly to the packages page
        flash(f'Welcome, {username}!', 'success')  # Flash a welcome message
        return redirect(url_for('packages'))  # Redirect to the packages page
    
    return render_template('index.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        fname = request.form.get('fname')
        minit = request.form.get('minit')
        lname = request.form.get('lname')
        password = request.form.get('password')
        contact_no = request.form.get('contact_no')
        role = request.form.get('role')  # role can be "admin" or "user"

        if not email or not password or not role:
            flash("Please fill out all fields", "error")
            return redirect(url_for('signin'))

        # Set RoleID based on the role selected during registration
        if role == 'admin':
            RoleID = 1
        else:
            RoleID = 2

        # SQL query to insert user details into the 'user' table without password hashing
        sql = """
            INSERT INTO user (Email, Fname, Minit, Lname, Password, ContactNo, RoleID)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (email, fname, minit, lname, password, contact_no, RoleID)

        cursor = db.cursor()
        try:
            # Insert user details into the 'user' table
            cursor.execute(sql, values)

            # Create a MySQL user based on the email
            cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (email, password))

            # Grant privileges based on the role
            if role == 'admin':
                cursor.execute("GRANT CREATE, SELECT, INSERT, UPDATE, DELETE ON travelmanagement.* TO %s@'localhost'", (email,))
            else:
                cursor.execute("GRANT SELECT, INSERT ON  travelmanagement.* TO %s@'localhost'", (email,))

            db.commit()  # Commit the changes
            flash("Registration successful!", "success")
            return redirect(url_for('login'))  # Redirect to login after successful registration
        except mysql.connector.Error as e:
            db.rollback()
            flash(f"Error: {e}", "error")
            return redirect(url_for('signin'))  # Redirect back to registration page in case of an error
        finally:
            cursor.close()

    return render_template('signin.html')




@app.route('/alluser', methods=['GET'])
def alluser():
    sql = "SELECT UserID, Fname AS FirstName, Lname AS LastName, Email FROM user"
    cursor = db.cursor(dictionary=True)
    cursor.execute(sql)
    users = cursor.fetchall()
    cursor.close()
    return render_template('user.html', users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Debugging: Print the email and password entered in the form
        print(f"Email: {email}")
        print(f"Password entered: {password}")

        # Retrieve user record based on email and password
        sql = "SELECT * FROM user WHERE Email = %s AND Password = %s"
        cursor = db.cursor(buffered=True)  # Use buffered=True to handle unread results
        cursor.execute(sql, (email, password))
        user = cursor.fetchone()
        cursor.close()

        # Debugging: Print the user record retrieved from the database
        print(f"User fetched from DB: {user}")

        # Check if user exists
        if user is None:
            flash("Invalid email or password, please try again.", "error")
            return redirect(url_for('login'))  # Redirect back to login page if user is not found

        # Access the user info from the tuple
        user_id = user[0]  # Assuming UserID is the first column (index 0)
        stored_password = user[5]  # Assuming Password is the 5th column (index 4)
        role_id = user[7]  # Assuming RoleID is the 8th column (index 7)

        # Debugging: Print the stored password from the DB
        print(f"Stored password: {stored_password}")

        # Check if the passwords match
        if password == stored_password:
            # Store user info in session
            session['user_id'] = user_id
            session['role'] = role_id  # Store the role in the session

            # Redirect based on user role
            if role_id == 1:  # Admin
                return redirect(url_for('admin_dashboard'))
            else:  # Regular user
                return redirect(url_for('view_packages'))  # Redirect user to packages page
        else:
            flash("Invalid credentials, please try again.", "error")
            return redirect(url_for('login'))  # Redirect back to login page if password is incorrect

    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if 'role' exists in the session and if it corresponds to an admin (role 1)
    if 'role' in session and session['role'] == 1:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT PackageID, Description, Price, last_modified FROM package")  # Fetch all packages
        packages = cursor.fetchall()
        cursor.close()
        
        # Render the admin dashboard template and pass the packages list
        return render_template('admin_dashboard.html', packages=packages)
    else:
        flash("Unauthorized access!", "error")
        return redirect(url_for('login'))  # Redirect to login if not authorized



# Route to add a new package
@app.route('/add_package', methods=['GET', 'POST'])
def add_package():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        price = request.form.get('price')
        description = request.form.get('description')
        availability = 1 if 'availability' in request.form else 0

        # Insert package data into the database (use your database connection and query)
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO package (StartDate, EndDate, Price, Description, Availability)
                VALUES (%s, %s, %s, %s, %s)
            """, (start_date, end_date, price, description, availability))
            db.commit()
            flash("Package added successfully!", "success")
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard on success
        except Exception as e:
            db.rollback()
            flash(f"Error adding package: {e}", "error")
            return redirect(url_for('add_package'))  # Stay on the form page if there's an error
        finally:
            cursor.close()
    
    # Render the form page
    return render_template('add_package.html')

@app.route('/packages', methods=['GET'])
def view_packages():
    cursor = db.cursor()
    query = "SELECT * FROM package WHERE Availability = 1"
    cursor.execute(query)
    packages = cursor.fetchall()
    cursor.close()
    
    # Check the role from the session
    if 'role' in session and session['role'] == 2:  # Regular user role ID is 2
        return render_template('packages.html', packages=packages)
    else:
        flash("Unauthorized access!", "error")
        return redirect(url_for('login'))
    
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/add-hotel', methods=['GET', 'POST'])

def add_hotel():
    if request.method == 'POST':
        hotel_name = request.form['name']
        hotel_rating = request.form['rating']
        hotel_price = request.form['price']
        hotel_location = request.form['location']
        package_id = request.form['package']  # Get the selected package ID

        # Insert the hotel into the 'hotel' table and associate it with the selected package
        query = """
            INSERT INTO hotel (Name, Rating, Price, Location)
            VALUES (%s, %s, %s, %s)
        """
        cursor = db.cursor()
        cursor.execute(query, (hotel_name, hotel_rating, hotel_price, hotel_location))
        hotel_id = cursor.lastrowid  # Get the last inserted hotel's ID
        db.commit()

        # Now associate the new hotel with the selected package in the package_hotel table
        package_hotel_query = """
            INSERT INTO package_hotel (PackageID, HotelID)
            VALUES (%s, %s)
        """
        cursor.execute(package_hotel_query, (package_id, hotel_id))
        db.commit()
        cursor.close()

        flash('Hotel added successfully and associated with the package!', 'success')
        return redirect(url_for('add_hotel'))

    # Fetch packages for the dropdown list from the 'package' table
    cursor = db.cursor()
    cursor.execute("SELECT PackageID, Description FROM package")  # Fetch package details
    packages = cursor.fetchall()
    cursor.close()

    return render_template('add_hotel.html', packages=packages)


# Route to view and select hotels for a specific package
@app.route('/packages/<int:package_id>/hotels', methods=['GET'])

def select_hotels(package_id):
    cursor = db.cursor(dictionary=True)
    
    # Fetch all hotels available for the specified package
    query = """
        SELECT * FROM hotel
        WHERE HotelID IN (SELECT HotelID FROM package_hotel WHERE PackageID = %s)
    """
    cursor.execute(query, (package_id,))
    hotels = cursor.fetchall()
    cursor.close()

    return render_template('hotels.html', hotels=hotels, package_id=package_id)

@app.route('/packages/<int:package_id>/transport', methods=['GET', 'POST'])

def view_transport(package_id):
    cursor = db.cursor(dictionary=True)
    
    # Fetch transport types
    cursor.execute("SELECT * FROM transporttype")
    transport_types = cursor.fetchall()

    # Initialize transports list
    transports = []

    selected_transport_type = request.form.get('transport_type')

    # Fetch transports based on selected transport type and the package_id
    if selected_transport_type:
        query = """
            SELECT * FROM transport
            WHERE TransportTypeID = %s AND Availability = 1 AND PackageID = %s
        """
        cursor.execute(query, (selected_transport_type, package_id))
        transports = cursor.fetchall()
    
    cursor.close()
    
    return render_template(
        'transport.html',
        package_id=package_id,
        transport_types=transport_types,
        transports=transports,
        selected_transport_type=selected_transport_type
    )


@app.route('/add-transport-type', methods=['GET', 'POST'])

def add_transport_type():
    if request.method == 'POST':
        transport_name = request.form['transport_name']
        
        # Insert the transport type into the database
        cursor = db.cursor()
        query = "INSERT INTO transporttype (TransportName) VALUES (%s)"
        cursor.execute(query, (transport_name,))
        db.commit()
        cursor.close()
        
        flash('Transport type added successfully!', 'success')
        return redirect(url_for('view_transport_types'))  # Redirect to a transport types view (to be created)

    return render_template('add_transport_type.html')

@app.route('/add-transport', methods=['GET', 'POST'])
def add_transport():
    cursor = db.cursor(dictionary=True)
    
    # Retrieve all transport types and packages for the dropdowns
    cursor.execute("SELECT * FROM transporttype")
    transport_types = cursor.fetchall()
    
    cursor.execute("SELECT PackageID, Description FROM package")  # Assuming 'packages' table exists with PackageID and PackageName
    packages = cursor.fetchall()
    
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        start_loc = request.form['start_loc']
        end_loc = request.form['end_loc']
        price = request.form['price']
        availability = int(request.form.get('availability', 0))
        transport_type_id = request.form['transport_type_id']
        package_id = request.form['package_id']  # Get selected package ID
        
        # Insert the transport details into the database
        query = """
            INSERT INTO transport (StartTime, EndTime, StartLoc, EndLoc, Price, Availability, TransportTypeID, PackageID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (start_time, end_time, start_loc, end_loc, price, availability, transport_type_id, package_id))
        db.commit()  # Ensure you commit the transaction
        
        flash('Transport added successfully!', 'success')
        
        # Redirect to a transport list view without package_id
        return redirect('/add-transport')

    cursor.close()
    return render_template('add_transport.html', transport_types=transport_types, packages=packages)


# Route to view all transport types (use this route for redirection)
@app.route('/transport-types')

def view_transport_types():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transporttype")
    transport_types = cursor.fetchall()
    cursor.close()
    return render_template('transport_types.html', transport_types=transport_types)

from flask import jsonify

@app.route('/packages/<int:package_id>/book', methods=['GET', 'POST'])
def book_package(package_id):
    cursor = db.cursor(dictionary=True)
    
    # Fetch transport types and hotels associated with the package
    cursor.execute("SELECT * FROM transporttype")
    transport_types = cursor.fetchall()
    
    cursor.execute(""" 
        SELECT h.* FROM hotel h
        JOIN package_hotel ph ON h.HotelID = ph.HotelID
        WHERE ph.PackageID = %s
    """, (package_id,))
    hotels = cursor.fetchall()
    
    cursor.execute("SELECT Price FROM package WHERE PackageID = %s", (package_id,))
    package = cursor.fetchone()
    package_price = package['Price'] if package else 0
    
    if request.method == 'POST':
        email = request.form['email']
        hotel_id = request.form['hotel_id']
        transport_id = request.form['transport_id']
        
        cursor.execute("SELECT UserID FROM user WHERE Email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            flash('No user found with the provided email.', 'danger')
            return render_template('book_package.html', package_id=package_id, transport_types=transport_types, hotels=hotels)

        user_id = user['UserID']

        # Call the stored procedure
        booking_status = ''
        total_amount = 0
        try:
            # Execute the stored procedure
            cursor.callproc('BookPackage', [user_id, package_id, hotel_id, transport_id, booking_status, total_amount])
            db.commit()

            # Retrieve OUT parameters after calling the procedure
            cursor.execute("SELECT @booking_status AS booking_status, @total_amount AS total_amount")
            result = cursor.fetchone()
            booking_status = result['booking_status']
            total_amount = result['total_amount']

            print("Booking Status:", booking_status)
            print("Total Amount:", total_amount)

            if booking_status == 'Success':
                # Insert a record into the bookings table
                cursor.execute("""
                    INSERT INTO bookings (TransportID, HotelID)
                    VALUES (%s, %s)
                """, (transport_id, hotel_id))
                db.commit()

                flash(f'Booking successful! Total amount: {total_amount}', 'success')
                return redirect(url_for('payment_success'))  # Make sure this route exists
            else:
                flash('Booking failed, please try again.', 'danger')

        except mysql.connector.Error as e:
            db.rollback()
            flash(f"Database error: {e}", 'danger')

        finally:
            cursor.close()

    return render_template('book_package.html', package_id=package_id, transport_types=transport_types, hotels=hotels)


@app.route('/get_transports/<int:transport_type_id>/<int:package_id>', methods=['GET'])
def get_transports(transport_type_id, package_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM transport
        WHERE TransportTypeID = %s AND PackageID = %s AND Availability = 1
    """, (transport_type_id, package_id))
    transports = cursor.fetchall()
    cursor.close()
    return jsonify(transports)

@app.route('/delete_package/<int:package_id>', methods=['POST'])
def delete_package(package_id):
    cursor = db.cursor()

    try:
        # First, delete dependent rows from the package_hotel table
        cursor.execute("DELETE FROM package_hotel WHERE PackageID = %s", (package_id,))
        
        # Then, delete the package record from the database
        cursor.execute("DELETE FROM package WHERE PackageID = %s", (package_id,))

        # Check if any row was affected (i.e., package existed)
        if cursor.rowcount > 0:
            db.commit()
            flash(f'Package with ID {package_id} deleted successfully.', 'success')
        else:
            flash('Package not found.', 'warning')

    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Database error: {e}", 'danger')
    
    finally:
        cursor.close()

    return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard after deletion

# Route to display update form and handle update logic
@app.route('/update_package/<int:package_id>', methods=['GET', 'POST'])
def update_package(package_id):
    cursor = db.cursor()
    
    if request.method == 'POST':
        new_price = request.form.get('price')
        
        try:
            # Update the package price
            cursor.execute("UPDATE package SET Price = %s WHERE PackageID = %s", (new_price, package_id))
            db.commit()
            flash(f'Package with ID {package_id} updated successfully.', 'success')
        except mysql.connector.Error as e:
            db.rollback()
            flash(f"Database error: {e}", 'danger')
        finally:
            cursor.close()

        return redirect(url_for('admin_dashboard'))
    
    else:
        # Fetch current package details to pre-fill in the form
        cursor.execute("SELECT Description, Price FROM package WHERE PackageID = %s", (package_id,))
        package = cursor.fetchone()
        cursor.close()

        if package:
            return render_template('update_package.html', package_id=package_id, package=package)
        else:
            flash('Package not found.', 'warning')
            return redirect(url_for('admin_dashboard'))


# Route for payment success page
@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

if __name__ == '__main__':
    app.run(debug=True)