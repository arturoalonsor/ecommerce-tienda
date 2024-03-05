from django.shortcuts import render, redirect
from .models import Product, Category, Profile, OrderItem, Order
from cart.views import cart_summary
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm, OrderCreateForm
from django import forms
from django.db.models import Q
import json
from cart.cart import Cart
import requests


def search(request):
	# manera de preguntarse si llenaron el formulario correspondiente
	if request.method == "POST":
		searched = request.POST['searched']
		# consultamos al db por el producto buscado
		# notar icontains y Q que son elementos de Django para hacer búsquedas complejas
		searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
		# evitamos los valores nulos
		if not searched:
			messages.success(request, "El producto no existe. Inténtelo de nuevo.")
			return render(request, "search.html", {})
		else:
			return render(request, "search.html", {'searched':searched})
	else:
		return render(request, "search.html", {})	


def update_info(request):
	if request.user.is_authenticated:
		current_user = Profile.objects.get(user__id=request.user.id)
		form = UserInfoForm(request.POST or None, instance=current_user)

		if form.is_valid():
			form.save()
			messages.success(request, "Información actualizada.")
			return redirect('home')
		return render(request, "update_info.html", {'form':form})
	else:
		messages.success(request, "Debe iniciar sesión para acceder a esa sección.")
		return redirect('home')



def update_password(request):
	if request.user.is_authenticated:
		current_user = request.user
		# testeamos método para saber si llenaron el formulario
		if request.method  == 'POST':
			form = ChangePasswordForm(current_user, request.POST)
			# validación de formulario
			if form.is_valid():
				form.save()
				messages.success(request, "Se actualizó la contraseña.")
				login(request, current_user)
				return redirect('update_user')
			else:
				for error in list(form.errors.values()):
					messages.error(request, error)
					return redirect('update_password')
		else:
			form = ChangePasswordForm(current_user)
			return render(request, "update_password.html", {'form':form})
	else:
		messages.success(request, "Debe iniciar sesión para ver esa página.")
		return redirect('home')
def update_user(request):
	if request.user.is_authenticated:
		current_user = User.objects.get(id=request.user.id)
		user_form = UpdateUserForm(request.POST or None, instance=current_user)

		if user_form.is_valid():
			user_form.save()

			login(request, current_user)
			messages.success(request, "Usuario actualizado")
			return redirect('home')
		return render(request, "update_user.html", {'user_form':user_form})
	else:
		messages.success(request, "Debe iniciar sesión para ver esa página.")
		return redirect('home')


def category_summary(request):
	categories = Category.objects.all()
	return render(request, 'category_summary.html', {"categories":categories})	

def category(request, foo):
	# reemplazamos guiones con espacios
	foo = foo.replace('-', ' ')
	# sacamos la categoria de la url
	try:
		# y buscamos la categoria
		category = Category.objects.get(name=foo)
		products = Product.objects.filter(category=category)
		return render(request, 'category.html', {'products':products, 'category':category})
	except:
		messages.success(request, ("Categoría inexistente"))
		return redirect('home')


def product(request,pk):
	product = Product.objects.get(id=pk)
	return render(request, 'product.html', {'product':product})


def home(request):
	products = Product.objects.all()
	return render(request, 'home.html', {'products':products})


def about(request):
	return render(request, 'about.html', {})	

def login_user(request):
	if request.method == "POST":
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(request, username=username, password=password)
		if user is not None:
			login(request, user)

			# recuperamos el carrito de compras guardado del usuario desde la base de datos.
			# Esto se hace utilizando con el modelo Profile y el campo old_cart.
			# El carrito de compras guardado se almacena como una cadena JSON en el campo old_cart.
			current_user = Profile.objects.get(user__id=request.user.id)
			saved_cart = current_user.old_cart
			# convertir string de db a dict
			if saved_cart:
				# convertir a diccionario con JSON
				converted_cart = json.loads(saved_cart)
				# añadimos el diccionario cargado a la sesion
				# obtenemos el carrito
				cart = Cart(request)
				# hacemos un loop del carrito y lo añadimos con la funcion db_add
				for key,value in converted_cart.items():
					cart.db_add(product=key, quantity=value)

			messages.success(request, ("Ha iniciado sesión."))
			return redirect('home')
		else:
			messages.success(request, ("Error. Inténtelo otra vez."))
			return redirect('login')

	else:
		return render(request, 'login.html', {})


def logout_user(request):
	logout(request)
	messages.success(request, ("Cerró sesión. Gracias por visitarnos."))
	return redirect('home')



def register_user(request):
	form = SignUpForm()
	if request.method == "POST":
		form = SignUpForm(request.POST)
		if form.is_valid():
			form.save()
			username = form.cleaned_data['username']
			password = form.cleaned_data['password1']
			# loguear usuario luego de autenticar con la funcion integrada de django
			user = authenticate(username=username, password=password)
			login(request, user)
			messages.success(request, ("Nombre de usuario creado. Complete el siguiente formulario."))
			return redirect('update_info')
		else:
			messages.success(request, ("Hubo un problema al registrarse. Inténtelo otra vez."))
			return redirect('register')
	else:
		return render(request, 'register.html', {'form':form})
	

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            dni = form.cleaned_data['dni']  # Obtener el DNI del formulario
            # Realizar la consulta a la API de RENIEC
            api_url = f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}"
            headers = {"Authorization": "Bearer apis-token-7658.ff96nXWNy0s4UIITUvpFH3fTOYzq2t6o"}
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Procesar la respuesta de la API
                # Por ejemplo, podrías obtener el nombre y apellido del DNI consultado
                first_name = data.get('nombres', '')
                last_name = data.get('apellidoPaterno', '') + ' ' + data.get('apellidoMaterno', '')
                
                # Continuar con la creación de la orden
                order = form.save(commit=False)
                order.first_name = first_name
                order.last_name = last_name
                order.save()
                
                products = cart.get_prods()
                quantities = cart.get_quants()
                
                for product in products:
                    quantity = quantities[str(product.id)]
                    OrderItem.objects.create(order=order, product=product, price=product.price, quantity=quantity)
                
                return render(request, 'order_created.html', {'order': order, 'cart': cart})
            else:
                messages.success("DNI inválido. Inténtelo de nuevo.")
                # Por ejemplo, mostrar un mensaje de error al usuario
                error_message = "Error al consultar la API de RENIEC. Por favor, intenta nuevamente más tarde."
                return render(request, 'order_create.html', {'cart': cart, 'form': form, 'error_message': error_message})
    else:
        form = OrderCreateForm()

    return render(request, 'order_create.html', {'cart': cart, 'form': form})