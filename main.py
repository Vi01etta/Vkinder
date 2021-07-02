import db
from vk_api.longpoll import VkLongPoll, VkEventType
import requests
from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import requests
from data_file import *

session = requests.Session()
vk_session = vk_api.VkApi(token=group_token)
longpoll = VkLongPoll(vk_session)

try:
    vk_session.auth(token_only=True)
except vk_api.AuthError as error_msg:
    print(error_msg)

def write_msg(user_id, message, attachment=''):
    vk_session.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7),
                                        'attachment': attachment})

def get_params(add_params: dict = None):
    params = {
        'access_token': user_token,
        'v': '5.131'
    }
    if add_params:
        params.update(add_params)
        pass
    return params


class VkBot:

    def __init__(self, user_id):
        self.user = db.User
        self.user_id = user_id
        self.username = self.user_name()
        self.commands = ["привет", "пока", "старт", "продолжить"]
        self.age = 0
        self.sex = 0
        self.city = 0
        self.sex = 0
        self.searching_user_id = 0
        self.top_photos = ''
        self.offset = 0

    def user_name(self):
        response = requests.get('https://api.vk.com/method/users.get', get_params({'user_ids': self.user_id}))
        for user_info in response.json()['response']:
            self.username = user_info['first_name'] + ' ' + user_info['last_name']
        return self.username

    def start_program(self):
        self.user_name()
        db.create_tables()
        write_msg(self.user_id, 'В каком городе будем искать?')
        for new_event in longpoll.listen():
            if new_event.type == VkEventType.MESSAGE_NEW and new_event.to_me:
                self.user_city(new_event.message)
                self.user_name()
                self.user_age()
                self.user_sex()
                self.user = db.User(vk_id=self.user_id, user_name=self.username,
                                    range_age='age_list', city=self.city)
                db.add_user(self.user)
                self.find_user()
                self.get_top_photos()
                write_msg(self.user_id,
                          f'Имя  и Фамилия: {self.username}\n \nСсылка на страницу: @id{self.searching_user_id}',
                          self.top_photos)
                return self.searching()

    def searching(self):
        write_msg(self.user_id, 'Понравился пользователь?')
        while True:
            for new_event in longpoll.listen():
                if new_event.type == VkEventType.MESSAGE_NEW and new_event.to_me:
                    if new_event.message.lower() == 'пока':
                        return self.new_message(new_event.message.lower())
                    elif new_event.message.lower() == 'да':
                        searching_user = db.DatingUser(vk_id=self.searching_user_id, user_name=self.username,
                                                       id_User=self.user.id)
                        db.add_user(searching_user)
                        write_msg(self.user_id, 'Пользователь добавлен в базу данных')
                    write_msg(self.user_id, 'Идет поиск...')
                    self.offset += 1
                    self.find_user()
                    self.get_top_photos()
                    write_msg(self.user_id,
                              f'Имя  и Фамилия: {self.username}\n Ссылка на страницу: @id{self.searching_user_id}',
                              self.top_photos)
                    write_msg(self.user_id, 'Понравился пользователь?')

    def user_age(self):
        write_msg(self.user_id, 'Введите желаемый возраст кандидата')
        for new_event in longpoll.listen():
            if new_event.type == VkEventType.MESSAGE_NEW and new_event.to_me:
                self.age = new_event.message
                return self.age

    def user_sex(self):
        find_message = f'Какой пол будем искать? Введите: \n 1 - женский\n 2 - мужской\n 3 - любой\n'
        write_msg(self.user_id, find_message)
        for new_event in longpoll.listen():
            if new_event.type == VkEventType.MESSAGE_NEW and new_event.to_me:
                self.sex = new_event.message
                try:
                    if int(self.sex) in [1, 2, 3]:
                        return self.sex
                    else:
                        write_msg(self.user_id, f'Некорректное значение')
                        return self.user_sex()
                except ValueError:
                    write_msg(self.user_id, f'Некорректное значение')
                    return

    def user_city(self, city):
        response = requests.get('https://api.vk.com/method/database.getCities',
                                get_params({'country_id': 1, 'count': 1, 'q': city}))
        user_info = response.json()['response']
        self.city = user_info['items'][0]['id']
        return self.city

    def find_user(self):
        try:
            response = requests.get('https://api.vk.com/method/users.search',
                                    get_params({'count': 1,
                                                'offset': self.offset,
                                                'city': self.city,
                                                'country': 1,
                                                'sex': self.sex,
                                                'age_from': self.age,
                                                'age_to': self.age,
                                                'fields': 'is_closed',
                                                'status': 6,
                                                'has_photo': 1}
                                               )
                                    )
            if response.json()['response']['items']:
                for searching_user_id in response.json()['response']['items']:
                    private = searching_user_id['is_closed']
                    if private:
                        self.offset += 1
                        self.find_user()
                    else:
                        self.searching_user_id = searching_user_id['id']
                        self.username = searching_user_id['first_name'] + ' ' + searching_user_id['last_name']
            else:
                self.offset += 1
                self.find_user()
        except KeyError:
            write_msg(self.user_id, f' попробуйте ввести другие критерии поиска')
            self.start_program()


    def get_top_photos(self):
        photos = []
        response = requests.get(
            'https://api.vk.com/method/photos.get',
            get_params({'owner_id': self.searching_user_id,
                        'album_id': 'profile',
                        'extended': 1}))
        try:
            sorted_response = sorted(response.json()['response']['items'],
                                     key=lambda x: x['likes']['count'], reverse=True)
            for photo_id in sorted_response:
                photos.append(f'''photo{self.searching_user_id}_{photo_id['id']}''')
            self.top_photos = ','.join(photos[:3])
            return self.top_photos
        except:
            pass

    def new_message(self, message):
        # Привет
        if message.lower() == self.commands[0]:
            return f"Здравствуйте, Вас приветствует чат-бот знакомств Vkinder! \n" \
                   f"Отправьте слово 'СТАРТ' чтобы начать подбор. \n" \
                   f"Чтобы завершить программу, напишите 'пока'."
        # Пока
        elif message.lower() == self.commands[1]:
            return f"До свидания!"
        # Старт
        elif message.lower() == self.commands[2]:
            return self.start_program()
        else:
            return f"Я не понимаю что Вы хотите, {self.username}."


if __name__ == '__main__':
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            bot = VkBot(event.user_id)
            write_msg(event.user_id, bot.new_message(event.text))
