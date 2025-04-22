from django.contrib.auth.base_user import BaseUserManager
import random


class CustomUserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, username, phone, gender, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        user_id = str(random.randint(10000000000, 99999999999))
        email = self.normalize_email(email)
        user = self.model(user_id=user_id, username=username, email=email, phone_number=phone, gender=gender, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, phone_number, gender, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, phone_number, gender, password, **extra_fields)
