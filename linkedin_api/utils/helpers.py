import datetime
import re
from typing import Any, Dict, List
from linkedin_api import model

def get_id_from_urn(urn):
    """
    Return the ID of a given Linkedin URN.

    Example: urn:li:fs_miniProfile:<id>
    """
    return urn.split(":")[3]


def get_urn_from_raw_update(raw_string):
    """
    Return the URN of a raw group update

    Example: urn:li:fs_miniProfile:<id>
    Example: urn:li:fs_updateV2:(<urn>,GROUP_FEED,EMPTY,DEFAULT,false)
    """
    return raw_string.split("(")[1].split(",")[0]


def get_update_author_name(d_included):
    """Parse a dict and returns, if present, the post author name

    :param d_included: a dict, as returned by res.json().get("included", {})
    :type d_raw: dict

    :return: Author name
    :rtype: str
    """
    try:
        return d_included["actor"]["name"]["text"]
    except KeyError:
        return ""
    except TypeError:
        return "None"


def get_update_old(d_included):
    """Parse a dict and returns, if present, the post old string

    :param d_included: a dict, as returned by res.json().get("included", {})
    :type d_raw: dict

    :return: Post old string. Example: '2 mo'
    :rtype: str
    """
    try:
        return d_included["actor"]["subDescription"]["text"]
    except KeyError:
        return ""
    except TypeError:
        return "None"


def get_update_content(d_included, base_url):
    """Parse a dict and returns, if present, the post content

    :param d_included: a dict, as returned by res.json().get("included", {})
    :type d_raw: dict
    :param base_url: site URL
    :type d_raw: str

    :return: Post content
    :rtype: str
    """
    try:
        return d_included["commentary"]["text"]["text"]
    except KeyError:
        return ""
    except TypeError:
        # Let's see if its a reshared post...
        try:
            # TODO: call Linkedin API to fetch that particular post and extract content
            urn = get_urn_from_raw_update(d_included["*resharedUpdate"])
            return f"{base_url}/feed/update/{urn}"
        except KeyError:
            return "IMAGE"
        except TypeError:
            return "None"


def get_update_author_profile(d_included, base_url):
    """Parse a dict and returns, if present, the URL corresponding the profile

    :param d_included: a dict, as returned by res.json().get("included", {})
    :type d_raw: dict
    :param base_url: site URL
    :type d_raw: str

    :return: URL with either company or member profile
    :rtype: str
    """
    try:
        urn = d_included["actor"]["urn"]
    except KeyError:
        return ""
    except TypeError:
        return "None"
    else:
        urn_id = urn.split(":")[-1]
        if "company" in urn:
            return f"{base_url}/company/{urn_id}"
        elif "member" in urn:
            return f"{base_url}/in/{urn_id}"


def get_update_url(d_included, base_url):
    """Parse a dict and returns, if present, the post URL

    :param d_included: a dict, as returned by res.json().get("included", {})
    :type d_raw: dict
    :param base_url: site URL
    :type d_raw: str

    :return: post url
    :rtype: str
    """
    try:
        urn = d_included["updateMetadata"]["urn"]
    except KeyError:
        return ""
    except TypeError:
        return "None"
    else:
        return f"{base_url}/feed/update/{urn}"


def append_update_post_field_to_posts_list(d_included, l_posts, post_key, post_value):
    """Parse a dict and returns, if present, the desired value. Finally it
    updates an already existing dict in the list or add a new dict to it

    :param d_included: a dict, as returned by res.json().get("included", {})
    :type d_raw: dict
    :param l_posts: a list with dicts
    :type l_posts: list
    :param post_key: the post field name to extract. Example: 'author_name'
    :type post_key: str
    :param post_value: the post value correspoding to post_key
    :type post_value: str

    :return: post list
    :rtype: list
    """
    elements_current_index = len(l_posts) - 1

    if elements_current_index == -1:
        l_posts.append({post_key: post_value})
    else:
        if not post_key in l_posts[elements_current_index]:
            l_posts[elements_current_index][post_key] = post_value
        else:
            l_posts.append({post_key: post_value})
    return l_posts


def parse_list_raw_urns(l_raw_urns):
    """Iterates a list containing posts URNS and retrieves list of URNs

    :param l_raw_urns: List containing posts URNs
    :type l_raw_posts: list

    :return: List of URNs
    :rtype: list
    """
    l_urns = []
    for i in l_raw_urns:
        l_urns.append(get_urn_from_raw_update(i))
    return l_urns


def parse_list_raw_posts(l_raw_posts, linkedin_base_url):
    """Iterates a unsorted list containing post fields and assemble a
    list of dicts, each one of them contains a post

    :param l_raw_posts: Unsorted list containing posts information
    :type l_raw_posts: list
    :param linkedin_base_url: Linkedin URL
    :type linkedin_base_url: str

    :return: List of dicts, each one of them is a post
    :rtype: list
    """
    l_posts = []
    for i in l_raw_posts:
        author_name = get_update_author_name(i)
        if author_name:
            l_posts = append_update_post_field_to_posts_list(
                i, l_posts, "author_name", author_name
            )

        author_profile = get_update_author_profile(i, linkedin_base_url)
        if author_profile:
            l_posts = append_update_post_field_to_posts_list(
                i, l_posts, "author_profile", author_profile
            )

        old = get_update_old(i)
        if old:
            l_posts = append_update_post_field_to_posts_list(i, l_posts, "old", old)

        content = get_update_content(i, linkedin_base_url)
        if content:
            l_posts = append_update_post_field_to_posts_list(
                i, l_posts, "content", content
            )

        url = get_update_url(i, linkedin_base_url)
        if url:
            l_posts = append_update_post_field_to_posts_list(i, l_posts, "url", url)

    return l_posts


def get_list_posts_sorted_without_promoted(l_urns, l_posts):
    """Iterates l_urns and looks for corresponding dicts in l_posts matching 'url' key.
    If found, removes this dict from l_posts and appends it to the returned list of posts

    :param l_urns: List of posts URNs
    :type l_urns: list
    :param l_posts: List of dicts, which each of them is a post
    :type l_posts: list

    :return: List of dicts, each one of them is a post
    :rtype: list
    """
    l_posts_sorted_without_promoted = []
    l_posts[:] = [d for d in l_posts if "Promoted" not in d.get("old")]
    for urn in l_urns:
        for post in l_posts:
            if urn in post["url"]:
                l_posts_sorted_without_promoted.append(post)
                l_posts[:] = [d for d in l_posts if urn not in d.get("url")]
                break
    return l_posts_sorted_without_promoted

def get_timestamp_from_entity_urn(entity_urn: str) -> datetime.datetime:
    urn_activity = re.search("(urn:li:activity:\d+)", entity_urn).group()
    post_id = urn_activity.split(":")[-1]
    post_id_binary = bin(int(post_id))
    first_41 = post_id_binary[:43]
    raw_timestamp = int(first_41, 2) / 1000

    timestamp = datetime.datetime.fromtimestamp(raw_timestamp, tz=datetime.timezone.utc)
    return timestamp

def elements_to_linkedin_activity(data: List[Dict[Any, Any]]) -> model.LinkedinProfileActivityData:
    activities_list: List[model.LinkedinActivity] = []
    for d in data:
        is_liked = is_reposted = is_shared = is_commented = False

        try:
            actor_urn: str = d["actor"]["urn"]

            if "company" in actor_urn:
                actor_type = "company"
            elif "member" in actor_urn:
                actor_type = "member"
        except:
            actor_urn = ""

        try:
            actor_name: str = d["actor"]["name"]["text"]
        except:
            actor_name = ""
    
        try:
            dash_entity_urn: str = d["dashEntityUrn"]
        except:
            dash_entity_urn = ""

        try:
            entity_urn: str = d["entityUrn"]
        except:
            entity_urn = ""

        try:
            actions = d["updateMetadata"]["updateActions"]["actions"]
            for a in actions:
                if a["actionType"] == "SHARE_VIA":
                    url: str = a["url"]
                    break
        except:
            url = ""

        try:
            shared_caption: str = d["resharedUpdate"]["commentary"]["text"]["text"]
            is_shared = True
        except:
            shared_caption = ""

        if not is_shared:
            try:
                header_text: str = d["header"]["text"]["text"]
                if "reposted this" in header_text:
                    is_reposted = True
                elif "commented on this" in header_text:
                    is_commented = True
                else:
                    # too many branches
                    is_liked = True
            except:
                pass

        highlighted_comment = ""
        highlighted_comment_datetime: datetime.datetime = datetime.datetime.now()
        if is_commented:
            try:
                highlighted_comment_data = d["highlightedComments"][0]
                highlighted_comment: str = highlighted_comment_data["commentV2"]["text"]
                highlighted_comment_timestamp: int = highlighted_comment_data["createdTime"]
                highlighted_comment_datetime: datetime.datetime = datetime.datetime.fromtimestamp(highlighted_comment_timestamp, tz=datetime.timezone.utc)
            except:
                highlighted_comment = ""
                highlighted_comment_timestamp = -1

        try:
            caption: str = d["commentary"]["text"]["text"]
        except:
            caption = ""

        try:
            post_urn: str = d["updateMetadata"]["urn"]
        except:
            post_urn = ""
                
        activity_data = model.LinkedinActivity(
            actor_urn= actor_urn,
            actor_type= actor_type,
            actor_name= actor_name,
            dash_entity_urn= dash_entity_urn,
            entity_urn= entity_urn,
            url= url,
            caption= caption,
            post_urn= post_urn,
            is_shared= is_shared,
            shared_caption= shared_caption,
            is_reposted= is_reposted,
            is_liked= is_liked,
            is_commented= is_commented,
            comment = highlighted_comment,
            comment_timestamp = highlighted_comment_datetime,
            timestamp = get_timestamp_from_entity_urn(entity_urn),
        )

        activities_list.append(activity_data)

    return activities_list
        
