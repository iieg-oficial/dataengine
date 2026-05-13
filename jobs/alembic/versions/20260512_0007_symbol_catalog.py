"""symbol catalog (categories + symbols + seed)

Revision ID: 0007_symbol_catalog
Revises: 0006_layer_icon_url
Create Date: 2026-05-12

Catalogo de simbolos administrable desde mariachi-admin.
Consumido por mapalab (panel de emojis en herramientas/mediciones) y por
el editor SLD de mariachi (shape 'point' con ExternalGraphic).

El seed con el catalogo inicial (8 categorias, ~1000 emojis) viene de
mapalab/frontend/src/pages/maps/helpers/emojiCatalog.js. Se inserta inline
para que `make prod-migration` y `make migrate` lo apliquen automaticamente.
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_symbol_catalog"
down_revision = "0006_layer_icon_url"
branch_labels = None
depends_on = None


SEED_CATALOG = [
    {
        "slug": "caras",
        "name": "Caras",
        "icon": "😀",
        "emojis": [
            "😀","😃","😄","😁","😆","😅","🤣","😂","🙂","🙃","😉","😊","😇","🥰","😍","🤩",
            "😘","😗","😚","😙","🥲","😋","😛","😜","🤪","😝","🤑","🤗","🤭","🤫","🤔","🤐",
            "🤨","😐","😑","😶","😏","😒","🙄","😬","🤥","😌","😔","😪","🤤","😴","😷","🤒",
            "🤕","🤢","🤮","🥴","😵","🤯","🤠","🥳","🥸","😎","🤓","🧐","😕","😟","🙁","☹️",
            "😮","😯","😲","😳","🥺","😦","😧","😨","😰","😥","😢","😭","😱","😖","😣","😞",
            "😓","😩","😫","🥱","😤","😡","😠","🤬","😈","👿","💀","☠️","🤡","👹","👺",
            "👻","👽","👾","🤖",
        ],
    },
    {
        "slug": "gestos",
        "name": "Gestos",
        "icon": "👋",
        "emojis": [
            "👋","🤚","🖐️","✋","🖖","👌","🤌","🤏","✌️","🤞","🤟","🤘","🤙","👈","👉","👆",
            "👇","☝️","👍","👎","✊","👊","🤛","🤜","👏","🙌","👐","🤲","🤝","🙏","✍️",
            "💅","🤳","💪","🦾","🦿","🦵","🦶","👂","🦻","👃","🧠","🫀","🫁","🦷","🦴","👀",
            "👁️","👅","👄","💋","👶","🧒","👦","👧","🧑","👱","👨","🧔","👩","🧓","👴","👵",
        ],
    },
    {
        "slug": "animales",
        "name": "Animales",
        "icon": "🐶",
        "emojis": [
            "🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐻‍❄️","🐨","🐯","🦁","🐮","🐷","🐽","🐸",
            "🐵","🙈","🙉","🙊","🐒","🐔","🐧","🐦","🐤","🐣","🐥","🦆","🦅","🦉","🦇","🐺",
            "🐗","🐴","🦄","🐝","🪱","🐛","🦋","🐌","🐞","🐜","🪰","🪲","🪳","🦟","🦗","🕷️",
            "🦂","🐢","🐍","🦎","🦖","🦕","🐙","🦑","🦐","🦞","🦀","🐡","🐠","🐟","🐬","🐳",
            "🐋","🦈","🐊","🐅","🐆","🦓","🦍","🦧","🐘","🦛","🦏","🐪","🐫","🦒","🦘","🦬",
            "🐃","🐂","🐄","🐎","🐖","🐏","🐑","🦙","🐐","🦌","🐕","🐩","🦮","🐈","🐈‍⬛","🪶",
            "🐓","🦃","🦤","🦚","🦜","🦢","🦩","🕊️","🐇","🦝","🦨","🦡","🦫","🦦","🦥","🐁",
            "🐀","🐿️","🦔","🐾","🐉","🐲","🌵","🎄","🌲","🌳","🌴","🪵","🌱","🌿","☘️","🍀",
            "🪴","🎋","🎍","🍃","🍂","🍁","🌾","🌺","🌻","🌹","🥀","🌷","🌼","🌸","💐","🍄","🪨",
        ],
    },
    {
        "slug": "comida",
        "name": "Comida",
        "icon": "🍔",
        "emojis": [
            "🍏","🍎","🍐","🍊","🍋","🍌","🍉","🍇","🍓","🫐","🍈","🍒","🍑","🥭","🍍","🥥",
            "🥝","🍅","🍆","🥑","🥦","🥬","🥒","🌶️","🫑","🌽","🥕","🫒","🧄","🧅","🥔","🍠",
            "🥐","🥯","🍞","🥖","🥨","🧀","🥚","🍳","🧈","🥞","🧇","🥓","🥩","🍗","🍖","🦴",
            "🌭","🍔","🍟","🍕","🫓","🥪","🥙","🧆","🌮","🌯","🫔","🥗","🥘","🫕","🥫","🍝",
            "🍜","🍲","🍛","🍣","🍱","🥟","🦪","🍤","🍙","🍚","🍘","🍥","🥠","🥮","🍢","🍡",
            "🍧","🍨","🍦","🥧","🧁","🍰","🎂","🍮","🍭","🍬","🍫","🍿","🍩","🍪","🌰","🥜",
            "🍯","🥛","🍼","🫖","☕","🍵","🧃","🥤","🧋","🍶","🍺","🍻","🥂","🍷","🥃","🍸",
            "🍹","🧉","🍾","🧊","🥄","🍴","🍽️","🥣","🥡","🥢","🧂",
        ],
    },
    {
        "slug": "viajes",
        "name": "Viajes",
        "icon": "🚗",
        "emojis": [
            "🚗","🚕","🚙","🚌","🚎","🏎️","🚓","🚑","🚒","🚐","🛻","🚚","🚛","🚜","🏍️","🛵",
            "🚲","🛴","🛹","🛼","🚏","🛣️","🛤️","🛞","🚨","🚥","🚦","🛑","🚧","⛽","🚢",
            "⛵","🛶","🚤","🛳️","⛴️","🛥️","🚀","🛸","🛩️","✈️","🚁","🛬","🛫","🪂","💺","🚂",
            "🚃","🚄","🚅","🚆","🚇","🚈","🚉","🚊","🚝","🚞","🚋","🏠","🏡","🏘️","🏚️",
            "🏗️","🏭","🏢","🏬","🏣","🏤","🏥","🏦","🏨","🏪","🏫","🏩","💒","🏛️","⛪","🕌",
            "🕍","🛕","🕋","⛩️","🏰","🏯","🗼","🗽","🗿","🏟️","🎡","🎢","🎠","⛲","⛱️","🏖️",
            "🏝️","🏜️","🌋","⛰️","🏔️","🗻","🏕️","⛺","🛖","🌁","🌃","🏙️","🌆","🌇","🌄","🌅",
            "🌉","🎆","🎇","🧨","✨","🎈","🎉","🎊","🎋","🎎","🎏","🎑","🧧","🎀","🎁","🎗️",
        ],
    },
    {
        "slug": "objetos",
        "name": "Objetos",
        "icon": "💡",
        "emojis": [
            "⌚","📱","📲","💻","⌨️","🖥️","🖨️","🖱️","🖲️","💾","💿","📀","🧮","🎥","🎞️","📽️",
            "📺","📷","📸","📹","📼","🔍","🔎","🕯️","💡","🔦","🏮","🪔","📔","📕","📖","📗",
            "📘","📙","📚","📓","📒","📃","📜","📄","📰","🗞️","📑","🔖","🏷️","✉️","📧","📨",
            "📩","📤","📥","📦","📫","📪","📬","📭","📮","🗳️","✏️","✒️","🖋️","🖊️","🖌️","🖍️",
            "📝","📁","📂","🗂️","📅","📆","🗒️","🗓️","📇","📈","📉","📊","📋","📌","📍","📎",
            "🖇️","📏","📐","✂️","🗃️","🗄️","🗑️","🔒","🔓","🔏","🔐","🔑","🗝️","🔨","🪓","⛏️",
            "⚒️","🛠️","🗡️","⚔️","🔫","🪃","🏹","🛡️","🪚","🔧","🪛","🔩","⚙️","🗜️","⚖️","🦯",
            "🔗","⛓️","🪝","🧰","🧲","🪜","⚗️","🧪","🧫","🧬","🔬","🔭","📡","💉","🩸","💊",
            "🩹","🩺","🚪","🛗","🪞","🪟","🛏️","🛋️","🪑","🚽","🪠","🚿","🛁","🪤","🪒","🧴",
        ],
    },
    {
        "slug": "simbolos",
        "name": "Símbolos",
        "icon": "❤️",
        "emojis": [
            "❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔","❣️","💕","💞","💓","💗","💖",
            "💘","💝","💟","☮️","✝️","☪️","🕉️","☸️","✡️","🔯","🕎","☯️","☦️","🛐","⛎","♈",
            "♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓","🆔","⚛️","🉑","☢️","☣️",
            "📴","📳","🈶","🈚","🈸","🈺","🈷️","✴️","🆚","💮","🉐","㊙️","㊗️","🈴","🈵","🈹",
            "🈲","🅰️","🅱️","🆎","🆑","🅾️","🆘","❌","⭕","🛑","⛔","📛","🚫","💯","💢","♨️",
            "🚷","🚯","🚳","🚱","🔞","📵","🚭","❗","❕","❓","❔","‼️","⁉️","🔅","🔆","〽️",
            "⚠️","🚸","🔱","⚜️","🔰","♻️","✅","🈯","💹","❇️","✳️","❎","🌐","💠","Ⓜ️","🌀",
            "💤","🏧","🚾","♿","🅿️","🛗","🈳","🈂️","🛂","🛃","🛄","🛅","🔣","ℹ️","🔤","🔡",
            "🔠","🆖","🆗","🆙","🆒","🆕","🆓","0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣",
            "9️⃣","🔟","🔢","#️⃣","*️⃣","⏏️","▶️","⏸️","⏯️","⏹️","⏺️","⏭️","⏮️","⏩","⏪","🔀",
            "🔁","🔂","⏫","⏬","◀️","🔼","🔽","➡️","⬅️","⬆️","⬇️","↗️","↘️","↙️","↖️","↕️",
            "↔️","↩️","↪️","⤴️","⤵️","🔃","🔄","🔙","🔚","🔛","🔜","🔝",
        ],
    },
    {
        "slug": "actividades",
        "name": "Actividades",
        "icon": "⚽",
        "emojis": [
            "⚽","🏀","🏈","⚾","🥎","🎾","🏐","🏉","🥏","🎱","🪀","🏓","🏸","🏒","🏑","🥍",
            "🏏","🪃","🥅","⛳","🪁","🏹","🎣","🤿","🥊","🥋","🎽","🛹","🛼","🛷","⛸️","🥌",
            "🎿","⛷️","🏂","🪂","🏋️","🤼","🤸","⛹️","🤺","🤾","🏌️","🏇","🧘","🏄","🏊","🤽",
            "🚣","🧗","🚵","🚴","🏆","🥇","🥈","🥉","🏅","🎖️","🏵️","🎗️","🎫","🎟️","🎪","🤹",
            "🎭","🩰","🎨","🎬","🎤","🎧","🎼","🎹","🥁","🪘","🎷","🎺","🪗","🎸","🪕","🎻",
            "🎲","♟️","🎯","🎳","🎮","🕹️","🧩","🪅","🪆","🎰","🧸",
        ],
    },
]


def upgrade() -> None:
    op.create_table(
        "symbol_categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        schema="mapalab",
    )

    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer,
            sa.ForeignKey("mapalab.symbol_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.String(16),
            sa.CheckConstraint(
                "kind IN ('emoji','svg','image')",
                name="ck_symbols_kind",
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("image_object_key", sa.Text, nullable=True),
        sa.Column("png_object_key", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        schema="mapalab",
    )

    op.create_index(
        "ix_symbols_category_sort",
        "symbols",
        ["category_id", "sort_order"],
        schema="mapalab",
    )

    bind = op.get_bind()

    categories_table = sa.table(
        "symbol_categories",
        sa.column("id", sa.Integer),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("icon", sa.Text),
        sa.column("sort_order", sa.Integer),
        schema="mapalab",
    )

    symbols_table = sa.table(
        "symbols",
        sa.column("category_id", sa.Integer),
        sa.column("kind", sa.String),
        sa.column("value", sa.Text),
        sa.column("sort_order", sa.Integer),
        schema="mapalab",
    )

    for cat_order, cat in enumerate(SEED_CATALOG):
        result = bind.execute(
            sa.insert(categories_table)
            .values(
                slug=cat["slug"],
                name=cat["name"],
                icon=cat["icon"],
                sort_order=cat_order,
            )
            .returning(categories_table.c.id)
        )
        category_id = result.scalar_one()

        rows = [
            {
                "category_id": category_id,
                "kind": "emoji",
                "value": emoji,
                "sort_order": idx,
            }
            for idx, emoji in enumerate(cat["emojis"])
        ]
        if rows:
            bind.execute(sa.insert(symbols_table), rows)


def downgrade() -> None:
    op.drop_index("ix_symbols_category_sort", table_name="symbols", schema="mapalab")
    op.drop_table("symbols", schema="mapalab")
    op.drop_table("symbol_categories", schema="mapalab")
