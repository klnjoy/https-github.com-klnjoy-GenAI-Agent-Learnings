{\rtf1\ansi\ansicpg1252\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # banking_system_oop.py\
from abc import ABC, abstractmethod\
from dataclasses import dataclass\
from datetime import datetime\
from enum import Enum\
from typing import Dict, List, Optional\
\
\
# ====================== Custom Exceptions ======================\
class BankingError(Exception):\
    """Base exception for banking operations"""\
    pass\
\
\
class InsufficientFundsError(BankingError):\
    pass\
\
\
class InvalidAmountError(BankingError):\
    pass\
\
\
# ====================== Enums ======================\
class AccountType(Enum):\
    SAVINGS = "savings"\
    CURRENT = "current"\
    LOAN = "loan"\
\
\
# ====================== Transaction Model ======================\
@dataclass\
class Transaction:\
    timestamp: datetime\
    type: str\
    amount: float\
    balance_after: float\
    description: str = ""\
\
\
# ====================== Abstract Base Class ======================\
class Account(ABC):\
    def __init__(self, name: str, initial_balance: float = 0.0):\
        if initial_balance < 0:\
            raise InvalidAmountError("Initial balance cannot be negative")\
       \
        self.name = name\
        self._balance = initial_balance\
        self._transactions: List[Transaction] = []\
        self._record_transaction("OPEN", initial_balance, "Account opened")\
\
    @property\
    def balance(self) -> float:\
        return self._balance\
\
    @abstractmethod\
    def calculate_interest(self) -> float:\
        """Calculate interest - must be implemented by subclasses"""\
        pass\
\
    def deposit(self, amount: float) -> None:\
        if amount <= 0:\
            raise InvalidAmountError("Deposit amount must be positive")\
       \
        self._balance += amount\
        self._record_transaction("DEPOSIT", amount, f"Deposited \{amount\}")\
        print(f"\{self.name\} deposited $\{amount:,.2f\}. New balance: $\{self._balance:,.2f\}")\
\
    def withdraw(self, amount: float) -> None:\
        if amount <= 0:\
            raise InvalidAmountError("Withdrawal amount must be positive")\
        if amount > self._balance:\
            raise InsufficientFundsError(\
                f"Insufficient funds. Available: $\{self._balance:,.2f\}"\
            )\
       \
        self._balance -= amount\
        self._record_transaction("WITHDRAW", amount, f"Withdrew \{amount\}")\
        print(f"\{self.name\} withdrew $\{amount:,.2f\}. New balance: $\{self._balance:,.2f\}")\
\
    def _record_transaction(self, tx_type: str, amount: float, description: str):\
        tx = Transaction(\
            timestamp=datetime.now(),\
            type=tx_type,\
            amount=amount,\
            balance_after=self._balance,\
            description=description\
        )\
        self._transactions.append(tx)\
\
    def show_transaction_history(self) -> None:\
        print(f"\\n--- Transaction History for \{self.name\} ---")\
        for tx in self._transactions[-10:]:  # Last 10 transactions\
            print(f"\{tx.timestamp.strftime('%Y-%m-%d %H:%M')\} | \{tx.type:8\} | "\
                  f"$\{tx.amount:10,.2f\} | Balance: $\{tx.balance_after:,.2f\} | \{tx.description\}")\
\
    def __str__(self) -> str:\
        return f"\{self.__class__.__name__\} - \{self.name\} | Balance: $\{self.balance:,.2f\}"\
\
\
# ====================== Concrete Account Classes ======================\
class SavingsAccount(Account):\
    INTEREST_RATE = 0.05  # 5%\
\
    def calculate_interest(self) -> float:\
        interest = self.balance * self.INTEREST_RATE\
        print(f"\{self.name\} earned interest: $\{interest:,.2f\} (5%)")\
        return interest\
\
\
class CurrentAccount(Account):\
    INTEREST_RATE = 0.02  # 2%\
\
    def calculate_interest(self) -> float:\
        interest = self.balance * self.INTEREST_RATE\
        print(f"\{self.name\} earned interest: $\{interest:,.2f\} (2%)")\
        return interest\
\
\
class LoanAccount(Account):\
    def __init__(self, name: str, initial_balance: float, loan_amount: float):\
        super().__init__(name, initial_balance)\
        if loan_amount <= 0:\
            raise InvalidAmountError("Loan amount must be positive")\
        self.loan_amount = loan_amount\
        self.interest_rate = 0.10  # 10%\
\
    def calculate_interest(self) -> float:\
        interest = self.loan_amount * self.interest_rate\
        print(f"\{self.name\}'s loan interest: $\{interest:,.2f\} (10%)")\
        return interest\
\
    def calculate_emi(self, months: int) -> float:\
        if months <= 0:\
            raise ValueError("Months must be positive")\
        emi = self.loan_amount / months\
        print(f"\{self.name\}'s EMI for \{months\} months: $\{emi:,.2f\}/month")\
        return emi\
\
\
# ====================== Bank Class (Composition) ======================\
class Bank:\
    def __init__(self, name: str = "Python National Bank"):\
        self.name = name\
        self.accounts: Dict[str, Account] = \{\}  # name -> Account\
\
    def create_account(self, acc_type: AccountType, name: str,\
                      initial_balance: float, **kwargs) -> Account:\
        if name in self.accounts:\
            raise BankingError(f"Account for \{name\} already exists!")\
\
        if acc_type == AccountType.SAVINGS:\
            account = SavingsAccount(name, initial_balance)\
        elif acc_type == AccountType.CURRENT:\
            account = CurrentAccount(name, initial_balance)\
        elif acc_type == AccountType.LOAN:\
            loan_amount = kwargs.get("loan_amount")\
            if not loan_amount:\
                raise ValueError("loan_amount required for LoanAccount")\
            account = LoanAccount(name, initial_balance, loan_amount)\
        else:\
            raise ValueError("Invalid account type")\
\
        self.accounts[name] = account\
        print(f"\{acc_type.value.capitalize()\} Account created successfully for \{name\}")\
        return account\
\
    def get_account(self, name: str) -> Optional[Account]:\
        return self.accounts.get(name)\
\
    def list_accounts(self) -> None:\
        if not self.accounts:\
            print("No accounts found.")\
            return\
        print(f"\\n=== \{self.name\} - All Accounts ===")\
        for account in self.accounts.values():\
            print(account)\
\
    def calculate_interest_all(self) -> None:\
        print(f"\\n=== Calculating Interest for All Accounts ===")\
        for account in self.accounts.values():\
            account.calculate_interest()\
\
\
# ====================== Main Application ======================\
def main():\
    bank = Bank()\
\
    while True:\
        print("\\n" + "="*50)\
        print(f"\{bank.name\} - MAIN MENU")\
        print("="*50)\
        print("1. Create Account")\
        print("2. Deposit")\
        print("3. Withdraw")\
        print("4. Show Balance")\
        print("5. Show All Accounts")\
        print("6. Calculate Interest (All)")\
        print("7. Loan EMI Calculator")\
        print("8. Transaction History")\
        print("9. Exit")\
        print("="*50)\
\
        choice = input("\\nEnter your choice (1-9): ").strip()\
\
        try:\
            if choice == "1":\
                print("\\nAccount Types: savings, current, loan")\
                acc_type_str = input("Enter account type: ").lower()\
                acc_type = AccountType(acc_type_str)\
                name = input("Enter customer name: ").strip()\
                balance = float(input("Enter initial balance: "))\
\
                if acc_type == AccountType.LOAN:\
                    loan_amt = float(input("Enter loan amount: "))\
                    bank.create_account(acc_type, name, balance, loan_amount=loan_amt)\
                else:\
                    bank.create_account(acc_type, name, balance)\
\
            elif choice == "2":\
                name = input("Enter account name: ").strip()\
                acc = bank.get_account(name)\
                if acc:\
                    amount = float(input("Enter deposit amount: "))\
                    acc.deposit(amount)\
                else:\
                    print("Account not found!")\
\
            elif choice == "3":\
                name = input("Enter account name: ").strip()\
                acc = bank.get_account(name)\
                if acc:\
                    amount = float(input("Enter withdrawal amount: "))\
                    acc.withdraw(amount)\
                else:\
                    print("Account not found!")\
\
            elif choice == "4":\
                name = input("Enter account name: ").strip()\
                acc = bank.get_account(name)\
                if acc:\
                    print(f"\{name\}'s current balance: $\{acc.balance:,.2f\}")\
                else:\
                    print("Account not found!")\
\
            elif choice == "5":\
                bank.list_accounts()\
\
            elif choice == "6":\
                bank.calculate_interest_all()\
\
            elif choice == "7":\
                name = input("Enter loan account name: ").strip()\
                acc = bank.get_account(name)\
                if isinstance(acc, LoanAccount):\
                    months = int(input("Enter number of months: "))\
                    acc.calculate_emi(months)\
                else:\
                    print("Loan account not found!")\
\
            elif choice == "8":\
                name = input("Enter account name: ").strip()\
                acc = bank.get_account(name)\
                if acc:\
                    acc.show_transaction_history()\
                else:\
                    print("Account not found!")\
\
            elif choice == "9":\
                print("Thank you for using Python National Bank!")\
                break\
\
            else:\
                print("Invalid choice! Please select 1-9.")\
\
        except ValueError as e:\
            print(f"Input error: \{e\}")\
        except BankingError as e:\
            print(f"Banking Error: \{e\}")\
        except Exception as e:\
            print(f"Unexpected error: \{e\}")\
\
\
if __name__ == "__main__":\
    main()\
}