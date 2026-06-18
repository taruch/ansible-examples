# Create Ansible Demo Database
# Usage: .\create_demo_database.ps1 -Server localhost -User sa -Password YourPassword

param(
    [string]$Server = "localhost",
    [string]$User = "sa",
    [string]$Password,
    [string]$Database = "ansible"
)

Write-Host "Creating database and populating with demo data..." -ForegroundColor Cyan

# Create database
try {
    $createDbQuery = @"
IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = '$Database')
BEGIN
    CREATE DATABASE [$Database];
    PRINT 'Database created';
END
ELSE
BEGIN
    PRINT 'Database already exists';
END
"@

    # Use -EncryptConnection for older SqlServer modules, skip for localhost
    if ($Server -eq "localhost" -or $Server -eq "." -or $Server -eq "(local)") {
        Invoke-Sqlcmd -Query $createDbQuery -ServerInstance $Server -Username $User -Password $Password -ErrorAction Stop
    } else {
        Invoke-Sqlcmd -Query $createDbQuery -ServerInstance $Server -Username $User -Password $Password -EncryptConnection:$false -ErrorAction Stop
    }
    Write-Host "Database check/creation completed" -ForegroundColor Green
} catch {
    Write-Host "Error creating database: $_" -ForegroundColor Red
    exit 1
}

# Create tables and populate data
try {
    $tablesQuery = @"
USE [$Database];

-- Users table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
BEGIN
    CREATE TABLE Users (
        UserID INT PRIMARY KEY IDENTITY(1,1),
        Username NVARCHAR(50) NOT NULL UNIQUE,
        Email NVARCHAR(100) NOT NULL,
        FirstName NVARCHAR(50),
        LastName NVARCHAR(50),
        Department NVARCHAR(50),
        JobTitle NVARCHAR(100),
        HireDate DATE,
        Salary DECIMAL(10,2),
        IsActive BIT DEFAULT 1,
        CreatedDate DATETIME DEFAULT GETDATE(),
        LastLoginDate DATETIME
    );
    PRINT 'Users table created';
END

-- Products table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
BEGIN
    CREATE TABLE Products (
        ProductID INT PRIMARY KEY IDENTITY(1,1),
        ProductName NVARCHAR(100) NOT NULL,
        Category NVARCHAR(50),
        Price DECIMAL(10,2),
        StockQuantity INT,
        Supplier NVARCHAR(100),
        Description NVARCHAR(500),
        IsDiscontinued BIT DEFAULT 0,
        CreatedDate DATETIME DEFAULT GETDATE()
    );
    PRINT 'Products table created';
END

-- Orders table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Orders')
BEGIN
    CREATE TABLE Orders (
        OrderID INT PRIMARY KEY IDENTITY(1,1),
        UserID INT FOREIGN KEY REFERENCES Users(UserID),
        ProductID INT FOREIGN KEY REFERENCES Products(ProductID),
        Quantity INT,
        UnitPrice DECIMAL(10,2),
        TotalAmount AS (Quantity * UnitPrice) PERSISTED,
        OrderDate DATETIME DEFAULT GETDATE(),
        ShipDate DATETIME,
        Status NVARCHAR(20) DEFAULT 'Pending',
        ShippingAddress NVARCHAR(200)
    );
    PRINT 'Orders table created';
END

-- Insert Users
IF NOT EXISTS (SELECT 1 FROM Users)
BEGIN
    INSERT INTO Users (Username, Email, FirstName, LastName, Department, JobTitle, HireDate, Salary, LastLoginDate)
    VALUES
        ('jdoe', 'john.doe@example.com', 'John', 'Doe', 'IT', 'DevOps Engineer', '2020-01-15', 95000.00, GETDATE()),
        ('asmith', 'alice.smith@example.com', 'Alice', 'Smith', 'IT', 'Senior Developer', '2019-03-22', 105000.00, GETDATE()),
        ('bwilliams', 'bob.williams@example.com', 'Bob', 'Williams', 'Sales', 'Sales Manager', '2018-07-10', 85000.00, DATEADD(day, -2, GETDATE())),
        ('cjohnson', 'carol.johnson@example.com', 'Carol', 'Johnson', 'HR', 'HR Director', '2017-05-01', 98000.00, DATEADD(day, -1, GETDATE())),
        ('dmiller', 'david.miller@example.com', 'David', 'Miller', 'IT', 'Database Administrator', '2020-09-12', 92000.00, GETDATE()),
        ('ebrown', 'emily.brown@example.com', 'Emily', 'Brown', 'Marketing', 'Marketing Specialist', '2021-02-28', 72000.00, DATEADD(hour, -3, GETDATE())),
        ('fdavis', 'frank.davis@example.com', 'Frank', 'Davis', 'Finance', 'Financial Analyst', '2019-11-05', 88000.00, DATEADD(day, -5, GETDATE())),
        ('gwilson', 'grace.wilson@example.com', 'Grace', 'Wilson', 'IT', 'Cloud Architect', '2018-04-18', 115000.00, GETDATE()),
        ('hmoore', 'henry.moore@example.com', 'Henry', 'Moore', 'Operations', 'Operations Manager', '2016-08-22', 102000.00, DATEADD(day, -3, GETDATE())),
        ('itaylor', 'ivy.taylor@example.com', 'Ivy', 'Taylor', 'IT', 'Security Engineer', '2021-06-14', 97000.00, GETDATE());
    PRINT 'Users inserted';
END

-- Insert Products
IF NOT EXISTS (SELECT 1 FROM Products)
BEGIN
    INSERT INTO Products (ProductName, Category, Price, StockQuantity, Supplier, Description)
    VALUES
        ('Dell PowerEdge R750', 'Hardware', 4500.00, 15, 'Dell Technologies', 'Rack server'),
        ('Cisco Catalyst 9300', 'Networking', 8200.00, 8, 'Cisco Systems', '48-port switch'),
        ('Red Hat Enterprise Linux', 'Software', 1299.00, 100, 'Red Hat', 'Enterprise Linux'),
        ('VMware vSphere', 'Software', 3495.00, 50, 'VMware', 'Virtualization'),
        ('HP ProBook 450', 'Hardware', 1200.00, 30, 'HP Inc', 'Laptop'),
        ('Ansible Automation Platform', 'Software', 5000.00, 25, 'Red Hat', 'Automation'),
        ('Fortinet FortiGate 60F', 'Security', 1850.00, 12, 'Fortinet', 'Firewall'),
        ('Microsoft SQL Server 2022', 'Software', 3717.00, 20, 'Microsoft', 'Database'),
        ('Lenovo ThinkPad X1', 'Hardware', 1850.00, 22, 'Lenovo', 'Ultrabook'),
        ('NetApp FAS2720', 'Storage', 12500.00, 5, 'NetApp', 'Storage'),
        ('AWS EC2 Credits', 'Cloud', 5000.00, 999, 'AWS', 'Cloud credits'),
        ('Docker Enterprise', 'Software', 2000.00, 40, 'Docker', 'Containers'),
        ('Dell UltraSharp', 'Hardware', 650.00, 45, 'Dell', 'Monitor'),
        ('Splunk Enterprise', 'Software', 8900.00, 15, 'Splunk', 'Analytics'),
        ('APC Smart-UPS', 'Hardware', 1299.00, 18, 'Schneider', 'UPS');
    PRINT 'Products inserted';
END

-- Insert Orders
IF NOT EXISTS (SELECT 1 FROM Orders)
BEGIN
    INSERT INTO Orders (UserID, ProductID, Quantity, UnitPrice, OrderDate, ShipDate, Status, ShippingAddress)
    VALUES
        (1, 1, 2, 4500.00, DATEADD(day, -30, GETDATE()), DATEADD(day, -28, GETDATE()), 'Delivered', '123 Main St, Boston'),
        (2, 5, 5, 1200.00, DATEADD(day, -25, GETDATE()), DATEADD(day, -23, GETDATE()), 'Delivered', '456 Oak Ave, SF'),
        (3, 6, 1, 5000.00, DATEADD(day, -20, GETDATE()), DATEADD(day, -18, GETDATE()), 'Delivered', '789 Pine Rd, Austin'),
        (4, 9, 3, 1850.00, DATEADD(day, -15, GETDATE()), DATEADD(day, -13, GETDATE()), 'Delivered', '321 Elm St, Seattle'),
        (5, 2, 1, 8200.00, DATEADD(day, -12, GETDATE()), DATEADD(day, -10, GETDATE()), 'Shipped', '654 Maple Dr, Denver'),
        (1, 13, 4, 650.00, DATEADD(day, -10, GETDATE()), NULL, 'Processing', '123 Main St, Boston'),
        (6, 3, 2, 1299.00, DATEADD(day, -8, GETDATE()), DATEADD(day, -6, GETDATE()), 'Delivered', '987 Cedar Ln, Portland'),
        (7, 4, 1, 3495.00, DATEADD(day, -7, GETDATE()), NULL, 'Pending', '147 Birch Ct, Phoenix'),
        (8, 10, 1, 12500.00, DATEADD(day, -5, GETDATE()), DATEADD(day, -3, GETDATE()), 'Delivered', '258 Spruce Way, Miami'),
        (9, 7, 2, 1850.00, DATEADD(day, -4, GETDATE()), NULL, 'Processing', '369 Ash Blvd, Chicago'),
        (10, 8, 1, 3717.00, DATEADD(day, -3, GETDATE()), NULL, 'Pending', '741 Walnut St, NY'),
        (2, 12, 3, 2000.00, DATEADD(day, -2, GETDATE()), NULL, 'Processing', '456 Oak Ave, SF'),
        (3, 14, 1, 8900.00, DATEADD(day, -1, GETDATE()), NULL, 'Pending', '789 Pine Rd, Austin'),
        (5, 15, 2, 1299.00, GETDATE(), NULL, 'Pending', '654 Maple Dr, Denver'),
        (1, 11, 10, 5000.00, GETDATE(), NULL, 'Pending', '123 Main St, Boston');
    PRINT 'Orders inserted';
END
"@

    if ($Server -eq "localhost" -or $Server -eq "." -or $Server -eq "(local)") {
        Invoke-Sqlcmd -Query $tablesQuery -ServerInstance $Server -Username $User -Password $Password -Database $Database -ErrorAction Stop
    } else {
        Invoke-Sqlcmd -Query $tablesQuery -ServerInstance $Server -Username $User -Password $Password -Database $Database -EncryptConnection:$false -ErrorAction Stop
    }
    Write-Host "Tables created and data populated" -ForegroundColor Green
} catch {
    Write-Host "Error creating tables: $_" -ForegroundColor Red
    exit 1
}

# Create view
try {
    $viewQuery = @"
USE [$Database];

IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_OrderSummary')
BEGIN
    CREATE VIEW vw_OrderSummary AS
    SELECT o.OrderID, u.Username, u.FirstName + ' ' + u.LastName AS CustomerName,
           p.ProductName, o.Quantity, o.UnitPrice, o.TotalAmount, o.OrderDate, o.Status
    FROM Orders o
    JOIN Users u ON o.UserID = u.UserID
    JOIN Products p ON o.ProductID = p.ProductID;
END
"@

    if ($Server -eq "localhost" -or $Server -eq "." -or $Server -eq "(local)") {
        Invoke-Sqlcmd -Query $viewQuery -ServerInstance $Server -Username $User -Password $Password -Database $Database -ErrorAction Stop
    } else {
        Invoke-Sqlcmd -Query $viewQuery -ServerInstance $Server -Username $User -Password $Password -Database $Database -EncryptConnection:$false -ErrorAction Stop
    }
    Write-Host "View created" -ForegroundColor Green
} catch {
    Write-Host "Error creating view: $_" -ForegroundColor Red
}

# Show stats
Write-Host "`n=== Database Statistics ===" -ForegroundColor Green
try {
    if ($Server -eq "localhost" -or $Server -eq "." -or $Server -eq "(local)") {
        $stats = Invoke-Sqlcmd -Query "SELECT (SELECT COUNT(*) FROM Users) AS Users, (SELECT COUNT(*) FROM Products) AS Products, (SELECT COUNT(*) FROM Orders) AS Orders, (SELECT SUM(TotalAmount) FROM Orders) AS Revenue" -ServerInstance $Server -Username $User -Password $Password -Database $Database
    } else {
        $stats = Invoke-Sqlcmd -Query "SELECT (SELECT COUNT(*) FROM Users) AS Users, (SELECT COUNT(*) FROM Products) AS Products, (SELECT COUNT(*) FROM Orders) AS Orders, (SELECT SUM(TotalAmount) FROM Orders) AS Revenue" -ServerInstance $Server -Username $User -Password $Password -Database $Database -EncryptConnection:$false
    }
    $stats | Format-Table -AutoSize
} catch {
    Write-Host "Could not retrieve statistics: $_" -ForegroundColor Yellow
}

Write-Host "`n=== Sample Orders ===" -ForegroundColor Green
try {
    if ($Server -eq "localhost" -or $Server -eq "." -or $Server -eq "(local)") {
        $orders = Invoke-Sqlcmd -Query "SELECT TOP 5 * FROM vw_OrderSummary ORDER BY OrderDate DESC" -ServerInstance $Server -Username $User -Password $Password -Database $Database
    } else {
        $orders = Invoke-Sqlcmd -Query "SELECT TOP 5 * FROM vw_OrderSummary ORDER BY OrderDate DESC" -ServerInstance $Server -Username $User -Password $Password -Database $Database -EncryptConnection:$false
    }
    $orders | Format-Table -AutoSize
} catch {
    Write-Host "Could not retrieve orders: $_" -ForegroundColor Yellow
}

Write-Host "`nDone! Database '$Database' created successfully." -ForegroundColor Green
